# -*- coding: utf-8 -*-
# Revisione R10 - 12/11/2026 - NIENTE PIU' OTTIMO TEORICO: main() cancella i vecchi file dell'ottimo (giornaliero.csv,
#   mensile.csv, indice.json, ULTIMO_CALCOLO.md, giorni/ della cartella cessione/) e non calcola altro; restano le funzioni
#   comuni (dati, prezzi, radiazione, fisica). Perdite di conversione dell'inverter (rendimento misurato a Cismondi per
#   fascia di potenza) e rendimenti/pesi della batteria da modelli/rendimenti_batteria.json (ml/rendimenti.py).
#   REVISIONE = R10
# Revisione R06 - 26/10/2026 - REVISIONE = R06 (nessun altro cambiamento)
# Revisione R05 - 26/10/2026 - carica 0-10 kW e scarica 2-10 kW (2 batterie da 5 kW; minimo 2 kW: solo nel modello non
#   lineare di cessione_ottimizza.py, l'ottimo teorico lineare non ha il minimo); REVISIONE = R05
# Revisione R04 - 24/10/2026 - ottimo() con valore finale dell'energia rimasta; REVISIONE = R04
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
R10: l'OTTIMO TEORICO dei giorni passati non si calcola piu' (main() cancella i suoi vecchi file). Restano le funzioni
  comuni (dati, prezzi, radiazione, fisica dell'impianto, programmazione lineare usata come seme dall'algoritmo evolutivo)
  usate da cessione_live.py (simulazione ogni 2 ore), cessione_ottimizza.py e cessione_apprendimento.py.
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
REVISIONE = "R10"
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
P_SCARICA_KW = 10.0              # 2 x 5 kW (R05: ogni batteria scarica tra 2 e 5 kW o e' ferma)
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
N_INVERTER = 2                   # 2 x SUN2000-10KTL-M1: la potenza si divide tra i due


# ------------------------------------------------------------------ R10: rendimenti misurati a Cismondi
def _rendimenti():
    """modelli/rendimenti_batteria.json (ml/rendimenti.py): rendimento dell'inverter per fascia (W per inverter), rendimenti
    e pesi della batteria per fascia di potenza (in % della potenza massima). Senza file: valori fissi."""
    r = {"inv_fasce_w": [500.0, 1000.0, 2000.0], "inv_eta": [0.97, 0.97, 0.97, 0.97], "inv_fonte": "ipotesi 0,97 (file mancante)",
         "soglie": [0.80, 0.90], "pesi_carica": [1.0, 0.98, 0.97], "pesi_scarica": [1.0, 0.98, 0.97],
         "eta_carica": [None, None, None], "eta_scarica": [None, None, None]}
    try:
        d = json.load(open(os.path.join(RADICE, "modelli", "rendimenti_batteria.json"), encoding="utf-8"))
        inv = d.get("inverter") or {}
        if len(inv.get("eta") or []) == 4:
            r["inv_fasce_w"] = [float(v) for v in inv.get("fasce_w") or r["inv_fasce_w"]]
            r["inv_eta"] = [min(1.0, max(0.8, float(v))) for v in inv["eta"]]
            r["inv_fonte"] = inv.get("fonte") or ""
        r["soglie"] = [float(v) for v in (d.get("regole") or {}).get("soglie") or r["soglie"]]
        for tipo in ("carica", "scarica"):
            b = d.get(tipo) or []
            if len(b) == 3:
                r["pesi_" + tipo] = [float(x["peso"]) for x in b]
                r["eta_" + tipo] = [float(x["eta"]) if x.get("valida") and x.get("eta") else None for x in b]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return r


REND = _rendimenti()


def eta_inverter(e_dc_q):
    """rendimento dell'inverter (array o numero) per l'energia DC di un quarto d'ora (kWh) divisa tra i 2 inverter"""
    p_w = np.asarray(e_dc_q, dtype=float) / Q * 1000 / N_INVERTER
    f, e = REND["inv_fasce_w"], REND["inv_eta"]
    return np.where(p_w < f[0], e[0], np.where(p_w < f[1], e[1], np.where(p_w < f[2], e[2], e[3])))


def fascia_potenza(e_q, p_max_kw):
    """fascia di potenza 0, 1, 2 (fino all'80 %, fino al 90 %, oltre) per l'energia di un quarto d'ora"""
    fr = np.asarray(e_q, dtype=float) / Q / p_max_kw
    s1, s2 = REND["soglie"]
    return np.where(fr <= s1 + 1e-9, 0, np.where(fr <= s2 + 1e-9, 1, 2))



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
        ac = pv * float(eta_inverter(pv))                  # R10: perdite di conversione dell'inverter
        ced = min(ac, LIM_Q)
        return 0.0, 0.0, ced, ac - ced, soc
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
    dc = pv - c + s
    ac = dc * float(eta_inverter(dc))                      # R10: perdite di conversione dell'inverter
    ced = min(ac, LIM_Q)
    tagl = ac - ced
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


# ------------------------------------------------------------------ R10: niente piu' ottimo teorico
VECCHI_FILE_OTTIMO = ("giornaliero.csv", "mensile.csv", "indice.json", "ULTIMO_CALCOLO.md")


def main():
    """R10 (decisione dell'utente 11/11/2026): l'ottimo teorico non si calcola piu' e i suoi file si cancellano.
    Restano cessione/live/ (simulazione ogni 2 ore), cessione/prezzi/ e cessione/meteo/ (usati dalla simulazione)."""
    import shutil
    tolti = []
    for nome in VECCHI_FILE_OTTIMO:
        f = os.path.join(OUT, nome)
        if os.path.isfile(f):
            os.remove(f)
            tolti.append(nome)
    cart = os.path.join(OUT, "giorni")
    if os.path.isdir(cart):
        n = len(os.listdir(cart))
        shutil.rmtree(cart)
        tolti.append(f"giorni/ ({n} file)")
    log("ottimo teorico non piu' calcolato (R10); " + (("cancellati i vecchi file: " + ", ".join(tolti)) if tolti
                                                      else "nessun vecchio file da cancellare"))


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:          # la simulazione principale non deve mai fermarsi per questa pagina
        print(f"Cessione totale: errore {ex}")
        sys.exit(0)
