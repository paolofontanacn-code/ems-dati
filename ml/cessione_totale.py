# -*- coding: utf-8 -*-
# Revisione R03 - 23/10/2026 - nuovo impianto: 20 kW a Ovest inclinazione 2 gradi, 2 inverter da 10 kW identici (calcolati
#   come uno da 20 kW), 2 batterie da 15 kWh (= 30 kWh, carica e scarica max 10 kW), rete max 17 kW, nessuna carica da AC;
#   produzione = Cismondi (11 kW, Sud, 2 gradi) x 20 / 11 x rapporto irraggiamento Ovest / Sud; funzioni comuni per la
#   simulazione ogni 2 ore (cessione_live.py). Tolto il profilo 1AC.
# Revisione R02 - 23/10/2026 - carica batteria max 5 kW; carica AC con perdita 5 % e solo se la carica DC non basta
# Revisione R01 - 23/10/2026 - batteria 15 kWh / 10 kW (prima 30); 2 inverter da 10 kW; profili 1 e 1AC
"""
cessione_totale.py - SOLO SIMULAZIONE: impianto FV da 20 kW in cessione totale (tutto il prodotto va in rete, RID).

Impianto (decisioni del 23/10/2026): 20 kW di pannelli a OVEST, inclinazione 2 gradi; 2 inverter SUN2000-10KTL-M1 identici
  e 2 batterie da 15 kWh, calcolati come un solo inverter da 20 kW con una batteria da 30 kWh (carica e scarica al massimo
  10 kW, perdita 5 % tra carica e scarica); verso la rete al massimo 17 kW; nessun prelievo dalla rete, nessuna carica da AC.
Produzione: letture Huawei a 5 minuti di Cismondi (11 kW, Sud, 2 gradi) x 20 / 11 x rapporto tra l'irraggiamento sul piano
  Ovest 2 gradi e sul piano Sud 2 gradi (modello isotropo, albedo 0,2), ora per ora, con la radiazione diretta e diffusa di
  Open-Meteo per il luogo di Cismondi (salvata in cessione/meteo/). Senza radiazione: rapporto con cielo sereno (segnalato).
Prezzi: vendita in RID al prezzo orario zonale NORD del GME (MGP).
Questo file calcola l'OTTIMO TEORICO dei giorni passati (produzione e prezzi noti in anticipo):
  0 = senza batteria;  1 = con batteria, programmazione lineare sul giorno e sul giorno dopo (massimo ricavo).
  Le funzioni comuni (dati, radiazione, fisica dell'impianto) sono usate anche da cessione_live.py (simulazione ogni 2 ore).
Uscite (cartella cessione/): giornaliero.csv, mensile.csv, indice.json, giorni/, ULTIMO_CALCOLO.md
"""
import base64
import csv
import datetime as dt
import glob
import gzip
import io
import json
import math
import os
import sys
import urllib.parse
import urllib.request
import zipfile
from zoneinfo import ZoneInfo

import numpy as np
from scipy.optimize import linprog

ROMA = ZoneInfo("Europe/Rome")
RADICE = os.environ.get("EMS_REPO_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATI = os.environ.get("EMS_DATI", os.path.join(RADICE, "memoria_mango"))
OUT = os.path.join(RADICE, "cessione")

# ------------------------------------------------------------------ parametri (decisioni del 23/10/2026)
REVISIONE = "R03"
P_CISMONDI_KW = 11.0             # Cismondi: 11 kW, Sud, inclinazione 2 gradi
P_IMPIANTO_KW = 20.0             # impianto simulato
SCALA = P_IMPIANTO_KW / P_CISMONDI_KW
INCLINAZIONE = 2.0               # gradi, Cismondi e impianto simulato
AZIMUT_CISMONDI = 0.0            # gradi dal Sud (0 = Sud, +90 = Ovest, -90 = Est)
AZIMUT_IMPIANTO = 90.0           # Ovest
ALBEDO = 0.2
P_INVERTER_KW = 20.0             # 2 x SUN2000-10KTL-M1 (10 kW nominali ciascuno)
LIMITE_RETE_KW = 17.0            # massimo verso la rete
CAPACITA_KWH = 30.0              # 2 x 15 kWh
P_CARICA_KW = 10.0               # 2 x 5 kW
P_SCARICA_KW = 10.0              # 2 x 5 kW
PERDITA_CICLO = 0.05             # tra energia caricata ed energia restituita
COPERTURA_MINIMA = 0.90          # giorni con meno del 90 % delle letture: mostrati ma esclusi dai totali
URL_GME = os.environ.get("EMS_PROVA_GME_API", "https://api.mercatoelettrico.org/request/api/v1")
URL_METEO = os.environ.get("EMS_PROVA_METEO", "https://api.open-meteo.com/v1/forecast")
MAX_DOWNLOAD_GIRO = 15           # giorni di prezzi scaricati dal GME al massimo per giro
MAX_METEO_GIRO = 30              # giorni di radiazione scaricati al massimo per giro
Q = 0.25                         # ore in un quarto d'ora
LIM_Q = min(LIMITE_RETE_KW, P_INVERTER_KW) * Q     # kWh massimi ceduti in un quarto d'ora
INV_Q = P_INVERTER_KW * Q
PC_Q, PS_Q, ETA = P_CARICA_KW * Q, P_SCARICA_KW * Q, 1 - PERDITA_CICLO



def log(msg):
    print(f"Cessione totale: {msg}", flush=True)


def numero(v):
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return None
    s = v.strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def campo(d, nome):
    if not isinstance(d, dict):
        return None
    if nome in d:
        return d[nome]
    n = nome.lower()
    for k, v in d.items():
        if str(k).lower().replace(" ", "") == n:
            return v
    return None


# ------------------------------------------------------------------ tempo
def mezzanotte(giorno):
    """timestamp della mezzanotte di Roma del giorno 'AAAA-MM-GG' e numero di quarti d'ora (92/96/100)"""
    d = dt.date.fromisoformat(giorno)
    t0 = dt.datetime(d.year, d.month, d.day, tzinfo=ROMA).timestamp()
    d1 = d + dt.timedelta(days=1)
    t1 = dt.datetime(d1.year, d1.month, d1.day, tzinfo=ROMA).timestamp()
    return int(t0), int(round((t1 - t0) / 900))


# ------------------------------------------------------------------ produzione
def letture_fv():
    """{giorno: {ts: fv_w}} dallo storico e dai giorni simulati chiusi (questi hanno la precedenza)"""
    per = {}

    def metti(ts, w):
        g = dt.datetime.fromtimestamp(ts, ROMA).strftime("%Y-%m-%d")
        per.setdefault(g, {})[ts] = w

    for f in sorted(glob.glob(os.path.join(RADICE, "storico", "storico_*.csv.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                t, w = numero(r.get("ts")), numero(r.get("fv_w"))
                if t is not None and w is not None:
                    metti(int(t), max(0.0, w))
    for f in sorted(glob.glob(os.path.join(RADICE, "dati", "????-??-??", "dataset.csv.gz"))):
        g = os.path.basename(os.path.dirname(f))
        nuove = {}
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                t, w = numero(r.get("ts")), numero(r.get("fv_w"))
                if t is not None and w is not None:
                    nuove[int(t)] = max(0.0, w)
        if nuove:
            vecchie = per.get(g, {})
            vecchie.update(nuove)
            per[g] = vecchie
    return per


def fv_quarti_cismondi(giorno, letture):
    """energia FV di Cismondi per quarto d'ora (kWh) e copertura delle letture (0..1)"""
    t0, nq = mezzanotte(giorno)
    somma, n = np.zeros(nq), np.zeros(nq)
    for ts, w in letture.items():
        k = int((ts - t0) // 900)
        if 0 <= k < nq:
            somma[k] += w
            n[k] += 1
    copertura = float(min(1.0, len(letture) / (nq * 3)))
    media = np.full(nq, np.nan)
    ok = n > 0
    media[ok] = somma[ok] / n[ok]
    if ok.any():
        idx = np.arange(nq)
        media = np.interp(idx, idx[ok], media[ok], left=0.0, right=0.0)   # buchi interni: interpolati; prima della
                                                                            # prima e dopo l'ultima lettura: 0
    else:
        media = np.zeros(nq)
    return media / 1000 * 0.25, copertura          # kWh del quarto d'ora a CISMONDI (Sud): scala e Ovest a parte


# ------------------------------------------------------------------ prezzi
def gme_token():
    f = os.path.join(RADICE, "mango", "gme_credenziali.json")
    if os.path.isfile(f):
        cred = json.load(open(f, encoding="utf-8"))
    elif os.environ.get("GME_LOGIN"):
        cred = {"Login": os.environ["GME_LOGIN"], "Password": os.environ.get("GME_PASSWORD", "")}
    else:
        raise RuntimeError("credenziali GME non disponibili")
    a = posta(URL_GME + "/Auth", cred)
    tok = campo(a, "token")
    if not campo(a, "Success") or not tok:
        raise RuntimeError(f"accesso al GME non riuscito: {campo(a, 'Reason')}")
    return tok


def posta(url, corpo, token=None):
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def gme_richiedi(token, g8, gran):
    r = posta(URL_GME + "/RequestData", {"Platform": "PublicMarketResults", "Segment": "MGP", "DataName": "ME_ZonalPrices",
                                         "IntervalStart": int(g8), "IntervalEnd": int(g8),
                                         "Attributes": {"GranularityType": gran}}, token)
    cont = campo(r, "ContentResponse")
    if not cont:
        raise RuntimeError(f"nessun dato GME {gran} per il {g8}: {campo(r, 'ResultRequest')}")
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(cont))) as z:
        nome = next((n for n in z.namelist() if n.lower().endswith(".json")), None)
        if not nome:
            raise RuntimeError("lo zip del GME non contiene un file JSON")
        righe = json.loads(z.read(nome).decode("utf-8"))
    per = {}
    for x in righe:
        fd = str(campo(x, "FlowDate") or "")
        zona = str(campo(x, "Zone") or "").upper().replace(" ", "")
        p = numero(campo(x, "Period"))
        if gran == "PT60" and (p is None or p < 1):          # dati orari reali: Period = 0, l'ora e' in Hour
            p = numero(campo(x, "Hour"))
        prezzo = numero(campo(x, "Price"))
        if fd in ("", g8) and zona == "NORD" and p and p >= 1 and prezzo is not None:
            per[int(p)] = prezzo / 1000                          # EUR/MWh -> EUR/kWh
    return per


def prezzi_giorno(giorno, nq, stato):
    """prezzo orario NORD (EUR/kWh) ripetuto sui 4 quarti d'ora di ogni ora, oppure (None, motivo)"""
    g8 = giorno.replace("-", "")
    cand = [os.path.join(RADICE, "dati", giorno, "prezzi.json"), os.path.join(DATI, "prezzi", f"prezzi_{g8}.json"),
            os.path.join(OUT, "prezzi", f"prezzi_{g8}.json")]
    d = None
    for f in cand:
        if os.path.isfile(f):
            try:
                d = json.load(open(f, encoding="utf-8"))
                break
            except ValueError:
                d = None
    if d is None:
        if stato["scaricati"] >= MAX_DOWNLOAD_GIRO:
            return None, "prezzi non ancora scaricati (limite del giro)"
        try:
            if stato.get("token") is None:
                stato["token"] = gme_token()
            nh = nq // 4
            ore = gme_richiedi(stato["token"], g8, "PT60")
            if any(h not in ore for h in range(1, nh + 1)):
                return None, f"prezzi orari GME incompleti per il {g8}"
            d = {"giorno": g8, "unita": "EUR/kWh", "zona": "NORD", "fonte": "GME",
                 "ore": [{"nord": ore[h]} for h in range(1, nh + 1)]}
            os.makedirs(os.path.join(OUT, "prezzi"), exist_ok=True)
            with open(os.path.join(OUT, "prezzi", f"prezzi_{g8}.json"), "w", encoding="utf-8") as fh:
                json.dump(d, fh)
            stato["scaricati"] += 1
        except Exception as e:
            stato["token"] = stato.get("token") or False
            return None, f"prezzi GME non scaricati: {e}"
    o = d.get("ore") or []                                    # RID: prezzo orario zonale NORD
    if len(o) * 4 == nq and all(isinstance(x, dict) and x.get("nord") is not None for x in o):
        return np.repeat(np.array([float(x["nord"]) for x in o]), 4), "ore"
    return None, "prezzi del giorno incompleti"



# ------------------------------------------------------------------ luogo e radiazione
def coordinate():
    """latitudine e longitudine di Cismondi: memoria della simulazione (impianto letto da FusionSolar)"""
    if os.environ.get("EMS_LAT") and os.environ.get("EMS_LON"):
        return float(os.environ["EMS_LAT"]), float(os.environ["EMS_LON"])
    f = os.path.join(DATI, "stato.json")
    if os.path.isfile(f):
        try:
            imp = json.load(open(f, encoding="utf-8")).get("impianto") or {}
            if imp.get("lat") is not None and imp.get("lon") is not None:
                return float(imp["lat"]), float(imp["lon"])
        except ValueError:
            pass
    f = os.path.join(OUT, "meteo", "luogo.json")
    if os.path.isfile(f):
        d = json.load(open(f, encoding="utf-8"))
        return float(d["lat"]), float(d["lon"])
    return None


def sole(ts, lat, lon):
    """posizione del sole (algoritmo NOAA semplificato): zenit e azimut in gradi (azimut 0 = Sud, +90 = Ovest)"""
    ts = np.asarray(ts, dtype=float)
    doy = np.array([dt.datetime.fromtimestamp(t, dt.timezone.utc).timetuple().tm_yday for t in ts])
    ore_utc = (ts % 86400) / 3600.0
    g = 2 * math.pi / 365.0 * (doy - 1 + (ore_utc - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g) + 0.000907 * np.sin(2 * g)
            - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    tst = ore_utc * 60 + eqt + 4 * lon
    ha = np.radians(tst / 4 - 180)
    la = math.radians(lat)
    cz = np.clip(math.sin(la) * np.sin(decl) + math.cos(la) * np.cos(decl) * np.cos(ha), -1, 1)
    zen = np.degrees(np.arccos(cz))
    az = np.degrees(np.arctan2(np.sin(ha), np.cos(ha) * math.sin(la) - np.tan(decl) * math.cos(la)))   # 0 = Sud, + = Ovest
    return zen, az


def irraggiamento_piano(ghi, dirh, dif, zen, az, incl, azp):
    """irraggiamento su un piano inclinato (modello isotropo): ghi, diretta e diffusa orizzontali in W/m2"""
    cz = np.cos(np.radians(zen))
    b, ap = math.radians(incl), math.radians(azp)
    cth = cz * math.cos(b) + np.sin(np.radians(zen)) * math.sin(b) * np.cos(np.radians(az) - ap)
    dni = np.where(cz > 0.05, dirh / np.maximum(cz, 0.05), 0.0)
    return np.maximum(0, dni * np.maximum(cth, 0)) + dif * (1 + math.cos(b)) / 2 + ghi * ALBEDO * (1 - math.cos(b)) / 2


def rapporto_ovest(ts_fine_ora, ghi, dirh, dif, lat, lon):
    """rapporto irraggiamento Ovest / Sud per ore che finiscono a ts_fine_ora (Open-Meteo: media dell'ora precedente)"""
    zen, az = sole(np.asarray(ts_fine_ora) - 1800, lat, lon)
    s = irraggiamento_piano(ghi, dirh, dif, zen, az, INCLINAZIONE, AZIMUT_CISMONDI)
    o = irraggiamento_piano(ghi, dirh, dif, zen, az, INCLINAZIONE, AZIMUT_IMPIANTO)
    return np.where(s > 5, o / np.maximum(s, 1e-9), 1.0)


def scarica_json(url, timeout=40):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def radiazione_giorno(giorno, luogo, stato):
    """radiazione oraria del giorno passato (salvata in cessione/meteo/rad_AAAAMMGG.json): {ts_fine_ora: [ghi, dir, dif]}"""
    f = os.path.join(OUT, "meteo", f"rad_{giorno.replace('-', '')}.json")
    if os.path.isfile(f):
        try:
            return {int(k): v for k, v in json.load(open(f, encoding="utf-8")).items()}
        except ValueError:
            pass
    if luogo is None or stato["meteo"] >= MAX_METEO_GIRO or stato.get("meteo_ko"):
        return None
    try:
        q = urllib.parse.urlencode({"latitude": luogo[0], "longitude": luogo[1], "start_date": giorno, "end_date": giorno,
                                    "hourly": "shortwave_radiation,direct_radiation,diffuse_radiation", "timeformat": "unixtime"})
        r = scarica_json(URL_METEO + "?" + q)
        h = r.get("hourly") or {}
        out = {}
        for i, t in enumerate(h.get("time") or []):
            v = [h.get(k, [None] * (i + 1))[i] for k in ("shortwave_radiation", "direct_radiation", "diffuse_radiation")]
            if all(isinstance(x, (int, float)) for x in v):
                out[int(t)] = v
        if len(out) < 20:
            raise RuntimeError(f"radiazione incompleta ({len(out)} ore)")
        os.makedirs(os.path.dirname(f), exist_ok=True)
        json.dump({str(k): v for k, v in out.items()}, open(f, "w", encoding="utf-8"))
        stato["meteo"] += 1
        return out
    except Exception as e:
        stato["meteo_ko"] = str(e)
        return None


def fattore_quarti(t0, nq, rad, luogo):
    """fattore per quarto d'ora: (20 / 11) x rapporto Ovest / Sud. Senza radiazione: rapporto con cielo sereno."""
    centri = t0 + np.arange(nq) * 900 + 450
    if luogo is None:
        return np.full(nq, SCALA), "senza luogo: solo proporzione 20/11"
    fine_ora = (np.floor((centri - 1) / 3600) + 1) * 3600            # ora che contiene il quarto d'ora
    if rad:
        v = np.array([rad.get(int(t), [0, 0, 0]) for t in fine_ora], dtype=float)
        r = rapporto_ovest(fine_ora, v[:, 0], v[:, 1], v[:, 2], *luogo)
        fonte = "radiazione Open-Meteo"
    else:
        zen, _ = sole(fine_ora - 1800, *luogo)
        cz = np.maximum(np.cos(np.radians(zen)), 0)
        ghi = 1000 * cz ** 1.15
        r = rapporto_ovest(fine_ora, ghi, 0.8 * ghi, 0.2 * ghi, *luogo)
        fonte = "cielo sereno (radiazione non disponibile)"
    return SCALA * r, fonte


# ------------------------------------------------------------------ fisica dell'impianto (un quarto d'ora, energie in kWh)
def passo(modo, pv, soc, carica_cmd=0.0, scarica_cmd=0.0, fascia="I"):
    """modo: 'senza' (senza batteria), 'fully' (Fully fed to grid), 'tou' (fascia C = carica, D = scarica, I = nessuna),
    'terzi' (Third-party dispatch con comandi). Ritorna (carica, scarica, ceduto, tagliato, soc_dopo)."""
    spazio = max(0.0, CAPACITA_KWH - soc)
    dispon = max(0.0, soc) * ETA                       # energia che la batteria puo' ancora consegnare
    c = s = 0.0
    if modo == "senza":
        ced = min(pv, LIM_Q)
        return 0.0, 0.0, ced, pv - ced, soc
    if modo == "fully":                                # massima immissione: eccedenza in batteria, scarica fino al limite
        if pv >= LIM_Q:
            c = min(pv - LIM_Q, PC_Q, spazio)
        else:
            s = min(PS_Q, LIM_Q - pv, dispon)
    elif modo == "tou":
        if fascia == "C":                              # FV prima in batteria (priorita' "Charge"), il resto in rete
            c = min(pv, PC_Q, spazio)
        elif fascia == "D":                            # scarica in rete, i pannelli hanno la precedenza sul limite
            s = min(PS_Q, dispon, max(0.0, LIM_Q - pv))
        else:                                          # fuori dalle fasce: solo l'eccedenza oltre il limite in batteria
            c = min(max(0.0, pv - LIM_Q), PC_Q, spazio)
    elif modo == "terzi":
        if scarica_cmd > 1e-9:                         # in scarica la batteria ha la precedenza, il FV in eccesso si perde
            s = min(scarica_cmd, PS_Q, dispon, LIM_Q)
        elif carica_cmd > 1e-9:                        # in carica il FV va prima in batteria
            c = min(carica_cmd, pv, PC_Q, spazio)
        else:
            c = min(max(0.0, pv - LIM_Q), PC_Q, spazio)
    ced = min(pv - c + s, LIM_Q)
    tagl = pv - c + s - ced
    return c, s, ced, tagl, soc + c - s / ETA


def ottimo(pv, prezzi, soc0, n_oggi=None, valore_finale=0.0):
    """programmazione lineare (massimo ricavo, produzione e prezzi noti): variabili c = carica dal FV, s = scarica,
    x = FV tagliato; ceduto = pv - c + s - x tra 0 e il limite. valore_finale = EUR/kWh riconosciuti all'energia
    che resta in batteria a fine orizzonte (x rendimento). Ritorna le serie dei primi n_oggi quarti."""
    n = len(pv)
    I, Z, L = np.eye(n), np.zeros((n, n)), np.tril(np.ones((n, n)))
    vf = float(valore_finale)
    costo = np.concatenate([prezzi - vf * ETA, -prezzi + vf, prezzi])
    A = [np.hstack([-I, I, -I]), np.hstack([I, -I, I]), np.hstack([I, Z, I]),
         np.hstack([L, -L / ETA, Z]), np.hstack([-L, L / ETA, Z])]
    b = [LIM_Q - pv, pv, pv, np.full(n, CAPACITA_KWH - soc0), np.full(n, soc0)]
    r = linprog(costo, A_ub=np.vstack(A), b_ub=np.concatenate(b),
                bounds=[(0, PC_Q)] * n + [(0, PS_Q)] * n + [(0, None)] * n, method="highs")
    if r.status != 0:
        raise RuntimeError(f"ottimizzazione non riuscita: {r.message}")
    v = r.x.copy(); v[v < 1e-9] = 0
    m = n_oggi or n
    c, s, x = v[:m], v[n:n + m], v[2 * n:2 * n + m]
    return c, s, x


# ------------------------------------------------------------------ ottimo teorico dei giorni passati
def main():
    os.makedirs(OUT, exist_ok=True)
    oggi = dt.datetime.now(ROMA).strftime("%Y-%m-%d")
    letture = letture_fv()
    giorni = sorted(g for g in letture if g < oggi)
    stato = {"scaricati": 0, "meteo": 0}
    luogo = coordinate()
    if luogo:
        os.makedirs(os.path.join(OUT, "meteo"), exist_ok=True)
        json.dump({"lat": luogo[0], "lon": luogo[1]}, open(os.path.join(OUT, "meteo", "luogo.json"), "w"))
    righe, note, soc = [], [], 0.0
    os.makedirs(os.path.join(OUT, "giorni"), exist_ok=True)
    cache = {}

    def dati(g):
        if g not in cache:
            fvc, cop = fv_quarti_cismondi(g, letture[g])
            t0, nq = mezzanotte(g)
            fatt, fonte_fv = fattore_quarti(t0, nq, radiazione_giorno(g, luogo, stato), luogo)
            pr, fonte = prezzi_giorno(g, nq, stato)
            cache[g] = (fvc * fatt, cop, t0, nq, pr, fonte, fonte_fv)
        return cache[g]

    riporti = []
    for i, g in enumerate(giorni):
        fv, cop, t0, nq, prezzi, fonte, fonte_fv = dati(g)
        if prezzi is None:
            note.append(f"{g}: {fonte}")
            soc = 0.0
            continue
        if fonte_fv != "radiazione Open-Meteo":
            note.append(f"{g}: produzione Ovest con {fonte_fv}")
        p0 = [passo("senza", v, 0.0) for v in fv]
        ced0 = np.array([x[2] for x in p0])
        dom = giorni[i + 1] if i + 1 < len(giorni) else None
        if dom and dom == (dt.date.fromisoformat(g) + dt.timedelta(days=1)).isoformat() and dati(dom)[4] is not None:
            fv2, pr2 = np.concatenate([fv, dati(dom)[0]]), np.concatenate([prezzi, dati(dom)[4]])
        else:
            fv2, pr2 = fv, prezzi
        try:
            c, s, x = ottimo(fv2, pr2, soc, nq)
        except Exception as e:
            note.append(f"{g}: {e}")
            continue
        ced1 = fv - c + s - x
        socq = soc + np.cumsum(c) - np.cumsum(s) / ETA
        e0, e1 = float((ced0 * prezzi).sum()), float((ced1 * prezzi).sum())
        righe.append({
            "giorno": g, "mese": g[:7], "valido": int(cop >= COPERTURA_MINIMA), "copertura": round(cop, 3), "prezzi": fonte,
            "produzione": fonte_fv, "fv_kwh": round(float(fv.sum()), 3), "prezzo_medio_eur_kwh": round(float(prezzi.mean()), 5),
            "prezzo_min_eur_kwh": round(float(prezzi.min()), 5), "prezzo_max_eur_kwh": round(float(prezzi.max()), 5),
            "p0_ceduti_kwh": round(float(ced0.sum()), 3), "p0_tagliati_kwh": round(float((fv - ced0).sum()), 3), "p0_eur": round(e0, 4),
            "p1_ceduti_kwh": round(float(ced1.sum()), 3), "p1_tagliati_kwh": round(float(x.sum()), 3), "p1_eur": round(e1, 4),
            "p1_carica_kwh": round(float(c.sum()), 3), "p1_scarica_kwh": round(float(s.sum()), 3),
            "p1_perdite_kwh": round(float(s.sum() / ETA - s.sum()), 3), "p1_cicli": round(float(c.sum()) / CAPACITA_KWH, 3),
            "p1_prezzo_carica": round(float((c * prezzi).sum() / c.sum()), 5) if c.sum() > 1e-6 else "",
            "p1_prezzo_scarica": round(float((s * prezzi).sum() / s.sum()), 5) if s.sum() > 1e-6 else "",
            "p1_beneficio_eur": round(e1 - e0, 4), "p1_energia_fine_kwh": round(float(socq[-1]), 3), "p1_riporto_eur": 0.0})
        riporti.append((len(righe) - 1, float(socq[-1]), (float((s * prezzi).sum() / s.sum()) if s.sum() > 1e-6 else None)))
        soc = float(socq[-1])
        with open(os.path.join(OUT, "giorni", f"{g}.json"), "w", encoding="utf-8") as fh:
            json.dump({"giorno": g, "inizio": t0, "revisione": REVISIONE, "p0_ceduto": [round(float(v), 4) for v in ced0],
                       "quarti": [{"fv": round(float(fv[k]), 4), "prezzo": round(float(prezzi[k]), 5), "carica": round(float(c[k]), 4),
                                   "scarica": round(float(s[k]), 4), "tagliato": round(float(x[k]), 4),
                                   "ceduto": round(float(ced1[k]), 4), "soc": round(float(socq[k]), 3)} for k in range(nq)]},
                      fh, separators=(",", ":"))
    # energia rimasta in batteria a mezzanotte: il suo valore passa al giorno in cui e' stata prodotta
    for j, (i, e_fine, pr_stesso) in enumerate(riporti):
        if e_fine < 1e-6:
            continue
        succ = riporti[j + 1] if j + 1 < len(riporti) and riporti[j + 1][0] == i + 1 else None
        pr = (succ[2] if succ and succ[2] is not None else None) or pr_stesso or righe[i]["prezzo_max_eur_kwh"]
        v = e_fine * ETA * pr
        for k, segno in ((i, 1), ((succ[0], -1) if succ else (None, 0))):
            if k is None:
                continue
            for col in ("p1_riporto_eur", "p1_eur", "p1_beneficio_eur"):
                righe[k][col] = round(righe[k][col] + segno * v, 4)
    col = list(righe[0].keys()) if righe else ["giorno"]
    with open(os.path.join(OUT, "giornaliero.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=col)
        w.writeheader()
        w.writerows(righe)
    cm = ["fv_kwh", "p0_ceduti_kwh", "p0_eur", "p1_ceduti_kwh", "p1_eur", "p1_scarica_kwh", "p1_perdite_kwh", "p1_beneficio_eur"]
    mesi = {}
    for r in righe:
        m = mesi.setdefault(r["mese"], {"mese": r["mese"], "giorni_validi": 0, "giorni_esclusi": 0, **{k: 0.0 for k in cm}})
        if not r["valido"]:
            m["giorni_esclusi"] += 1
            continue
        m["giorni_validi"] += 1
        for k in cm:
            m[k] += r[k]
    with open(os.path.join(OUT, "mensile.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["mese", "giorni_validi", "giorni_esclusi"] + cm)
        w.writeheader()
        for m in sorted(mesi):
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in mesi[m].items()})
    indice = {"aggiornato": dt.datetime.now(ROMA).isoformat(timespec="seconds"), "revisione": REVISIONE,
              "parametri": {"p_cismondi_kw": P_CISMONDI_KW, "p_impianto_kw": P_IMPIANTO_KW, "scala": round(SCALA, 5),
                            "inclinazione": INCLINAZIONE, "azimut_cismondi": AZIMUT_CISMONDI, "azimut_impianto": AZIMUT_IMPIANTO,
                            "p_inverter_kw": P_INVERTER_KW, "limite_rete_kw": LIMITE_RETE_KW, "capacita_kwh": CAPACITA_KWH,
                            "potenza_carica_kw": P_CARICA_KW, "potenza_scarica_kw": P_SCARICA_KW, "perdita_ciclo": PERDITA_CICLO,
                            "copertura_minima": COPERTURA_MINIMA},
              "luogo": list(luogo) if luogo else None, "giorni": len(righe), "note": note[-60:],
              "meteo_errore": stato.get("meteo_ko")}
    with open(os.path.join(OUT, "indice.json"), "w", encoding="utf-8") as fh:
        json.dump(indice, fh, ensure_ascii=False, indent=1)
    validi = [r for r in righe if r["valido"]]
    tot = lambda k: sum(r[k] for r in validi)
    testo = [f"# Cessione totale 20 kW - ottimo teorico, ultimo calcolo {dt.datetime.now(ROMA):%d/%m/%Y %H:%M} ({REVISIONE})", "",
             f"Giorni calcolati: {len(righe)} (validi {len(validi)}). Note: {len(note)}.", "",
             f"Profilo 0 (senza batteria): {tot('p0_ceduti_kwh'):.1f} kWh ceduti, {tot('p0_eur'):.2f} EUR",
             f"Profilo 1 (batteria {CAPACITA_KWH:g} kWh, carica/scarica {P_CARICA_KW:g}/{P_SCARICA_KW:g} kW, ottimo teorico): "
             f"{tot('p1_ceduti_kwh'):.1f} kWh ceduti, {tot('p1_eur'):.2f} EUR, beneficio {tot('p1_beneficio_eur'):.2f} EUR", ""] + \
            [f"- {n}" for n in note[-60:]]
    with open(os.path.join(OUT, "ULTIMO_CALCOLO.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(testo) + "\n")
    log(f"ottimo teorico: {len(righe)} giorni ({len(validi)} validi), prezzi scaricati {stato['scaricati']}, radiazione "
        f"scaricata {stato['meteo']} giorni, beneficio batteria {tot('p1_beneficio_eur'):.2f} EUR; note: {len(note)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:          # la simulazione principale non deve mai fermarsi per questa pagina
        print(f"Cessione totale: errore {ex}")
        sys.exit(0)
