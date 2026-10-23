# -*- coding: utf-8 -*-
# Revisione R01 - 23/10/2026 - batteria 15 kWh / 10 kW (prima 30); 2 inverter da 10 kW (FV meta' e meta'), batteria
#   sull'inverter A; due simulazioni con batteria: 1 senza carica AC, 1AC con carica AC dall'inverter B (mai dalla rete)
"""
cessione_totale.py - SOLO SIMULAZIONE: impianto FV da 20 kW in cessione totale (tutto il prodotto va in rete, RID).

Produzione: letture Huawei a 5 minuti dell'impianto di Cismondi (11,48 kW, inclinazione simile) x 20 / 11,48.
  - giorni prima dell'avvio della simulazione: storico/storico_AAAAMM.csv.gz
  - giorni simulati (chiusi): dati/AAAA-MM-GG/dataset.csv.gz
Prezzi: oggi l'impianto vende in RID al prezzo orario (PO) zonale NORD: si usano i prezzi ORARI NORD del GME (MGP).
  - dati/AAAA-MM-GG/prezzi.json (gia' scaricati dalla simulazione) oppure scaricati dal GME e salvati in
    cessione/prezzi/prezzi_AAAAMMGG.json (una volta sola per giorno).
Impianto: 2 inverter da 10 kW, FV diviso a meta' (10 kW di pannelli per inverter); 1 sola batteria, sull'inverter A
  (ibrido, accoppiata in corrente continua). Uscita totale verso la rete al massimo LIMITE_RETE_KW. Prelievo dalla rete: 0.
Profili:
  0   = senza batteria: ceduto = prodotto (ogni inverter al massimo 10 kW, totale al massimo LIMITE_RETE_KW)
  1   = con batteria (CAPACITA_KWH, POTENZA_BATTERIA_KW) caricata SOLO dal FV dell'inverter A (lato continua)
  1AC = come 1, piu' carica AC: la batteria si puo' caricare anche con l'energia prodotta dall'inverter B, passando
        dal lato alternata dell'inverter A; MAI dalla rete (prelievo 0 in ogni quarto d'ora)
  Con la batteria si immagazzina nei quarti d'ora a prezzo di cessione piu' basso e si restituisce in quelli a prezzo
  piu' alto (programmazione lineare, massimo ricavo; prezzi del giorno e del giorno dopo, orizzonte mobile).
  Perdita tra carica e scarica: PERDITA_CICLO (5 %), uguale per carica dal FV e carica AC. Usura NON conteggiata.
Uscite (cartella cessione/): giornaliero.csv, mensile.csv, indice.json, ULTIMO_CALCOLO.md
"""
import base64
import csv
import datetime as dt
import glob
import gzip
import io
import json
import os
import sys
import urllib.request
import zipfile
from zoneinfo import ZoneInfo

import numpy as np
from scipy.optimize import linprog

ROMA = ZoneInfo("Europe/Rome")
RADICE = os.environ.get("EMS_REPO_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(RADICE, "cessione")

# ------------------------------------------------------------------ parametri (decisioni del 23/10/2026)
P_CISMONDI_KW = 11.48            # potenza dell'impianto di Cismondi (dati Huawei)
P_IMPIANTO_KW = 20.0             # impianto simulato in cessione totale
LIMITE_RETE_KW = 15.0            # potenza massima in uscita verso la rete
CAPACITA_KWH = 15.0              # batteria del profilo 1 (capacita' utile) - R01: 15 kWh (prima 30)
POTENZA_BATTERIA_KW = 10.0       # potenza massima di carica e di scarica
P_INVERTER_KW = 10.0             # ognuno dei 2 inverter (A con batteria, B senza)
QUOTA_FV_A = 0.5                 # FV sull'inverter A (il resto sul B)
PERDITA_CICLO = 0.05             # 5 % di perdita tra energia caricata ed energia restituita
COPERTURA_MINIMA = 0.90          # giorni con meno del 90 % delle letture: mostrati ma esclusi dai totali
SCALA = P_IMPIANTO_KW / P_CISMONDI_KW
REVISIONE = "R01"
URL_GME = os.environ.get("EMS_PROVA_GME_API", "https://api.mercatoelettrico.org/request/api/v1")
MAX_DOWNLOAD_GIRO = 15           # giorni di prezzi scaricati dal GME al massimo per giro


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


def fv_quarti(giorno, letture):
    """energia FV dell'impianto da 20 kW per quarto d'ora (kWh) e copertura delle letture (0..1)"""
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
    return media * SCALA / 1000 * 0.25, copertura


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
    cand = [os.path.join(RADICE, "dati", giorno, "prezzi.json"), os.path.join(OUT, "prezzi", f"prezzi_{g8}.json")]
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


# ------------------------------------------------------------------ simulazione di un giorno
def profilo0(fv, prezzi):
    a, b = fv * QUOTA_FV_A, fv * (1 - QUOTA_FV_A)
    pi = P_INVERTER_KW * 0.25
    ceduto = np.minimum(np.minimum(a, pi) + np.minimum(b, pi), LIMITE_RETE_KW * 0.25)
    return {"ceduti_kwh": ceduto.sum(), "tagliati_kwh": (fv - ceduto).sum(), "eur": float((ceduto * prezzi).sum())}


def profilo_batteria(fv, prezzi, soc0, n_oggi=None, carica_ac=False):
    """programmazione lineare sul giorno e, se noto, sul giorno dopo; si tengono solo le decisioni del giorno.
    Energie per quarto d'ora (kWh): a, b = FV sugli inverter A e B; variabili cd = carica dal FV di A (continua),
    ca = carica AC dall'inverter B (solo se carica_ac), s = scarica, xa, xb = FV tagliato su A e B.
    Uscita AC di A = a - cd - xa + s - ca (tra -10 e +10 kW), uscita di B = b - xb (<= 10 kW),
    ceduto = somma delle due: tra 0 (nessun prelievo dalla rete) e il limite verso la rete."""
    n = len(fv)
    a, b = fv * QUOTA_FV_A, fv * (1 - QUOTA_FV_A)
    lim, pb, pi, eta = LIMITE_RETE_KW * 0.25, POTENZA_BATTERIA_KW * 0.25, P_INVERTER_KW * 0.25, 1 - PERDITA_CICLO
    I, Z, L = np.eye(n), np.zeros((n, n)), np.tril(np.ones((n, n)))
    # ordine delle variabili: cd, ca, s, xa, xb ; ricavo = p.(a + b - cd - ca + s - xa - xb)
    costo = np.concatenate([prezzi, prezzi, -prezzi, prezzi, prezzi])
    A, B = [], []
    def riga(cd, ca, s_, xa, xb, lim_):
        A.append(np.hstack([cd, ca, s_, xa, xb])); B.append(lim_)
    riga(I, Z, Z, I, Z, a)                                    # cd + xa <= a
    riga(Z, Z, Z, Z, I, b)                                    # xb <= b
    riga(-I, -I, I, -I, Z, pi - a)                            # uscita di A <= 10 kW
    riga(I, I, -I, I, Z, pi + a)                              # uscita di A >= -10 kW (assorbe in carica AC)
    riga(Z, Z, Z, Z, -I, pi - b)                              # uscita di B <= 10 kW
    riga(-I, -I, I, -I, -I, lim - a - b)                      # ceduto <= limite verso la rete
    riga(I, I, -I, I, I, a + b)                               # ceduto >= 0: mai prelievo dalla rete
    riga(I, I, Z, Z, Z, np.full(n, pb))                       # potenza di carica della batteria
    riga(L, L, -L / eta, Z, Z, np.full(n, CAPACITA_KWH - soc0))   # energia in batteria <= capacita'
    riga(-L, -L, L / eta, Z, Z, np.full(n, soc0))                 # energia in batteria >= 0
    lim_var = [(0, pb)] * n + [(0, pb if carica_ac else 0)] * n + [(0, pb)] * n + [(0, None)] * n + [(0, None)] * n
    r = linprog(costo, A_ub=np.vstack(A), b_ub=np.concatenate(B), bounds=lim_var, method="highs")
    if r.status != 0:
        raise RuntimeError(f"ottimizzazione non riuscita: {r.message}")
    v = r.x.copy(); v[v < 1e-9] = 0
    cd, ca, s_, xa, xb = (v[k * n:(k + 1) * n] for k in range(5))
    m = n_oggi or n
    fv, prezzi, a, b, cd, ca, s_, xa, xb = (x[:m] for x in (fv, prezzi, a, b, cd, ca, s_, xa, xb))
    c = cd + ca
    ceduto = a + b - cd - ca + s_ - xa - xb
    soc = soc0 + np.cumsum(c) - np.cumsum(s_) / eta
    return {"ceduti_kwh": ceduto.sum(), "tagliati_kwh": (xa + xb).sum(), "eur": float((ceduto * prezzi).sum()),
            "carica_kwh": c.sum(), "carica_ac_kwh": ca.sum(), "scarica_kwh": s_.sum(), "perdite_kwh": s_.sum() / eta - s_.sum(),
            "soc_fine_kwh": float(soc[-1]), "prelievo_max_kwh": float(max(0.0, -ceduto.min())),
            "prezzo_carica": float((c * prezzi).sum() / c.sum()) if c.sum() > 1e-6 else None,
            "prezzo_scarica": float((s_ * prezzi).sum() / s_.sum()) if s_.sum() > 1e-6 else None,
            "quarti": [{"fv": round(float(fv[k]), 4), "prezzo": round(float(prezzi[k]), 5), "carica": round(float(c[k]), 4),
                        "carica_ac": round(float(ca[k]), 4), "scarica": round(float(s_[k]), 4),
                        "tagliato": round(float(xa[k] + xb[k]), 4), "soc": round(float(soc[k]), 3)} for k in range(m)]}


PROFILI_BATT = (("p1", False), ("p1ac", True))     # 1 = senza carica AC, 1AC = con carica AC dall'inverter B


# ------------------------------------------------------------------ principale
COL_MESE = ["fv_kwh", "p0_ceduti_kwh", "p0_eur"] + [f"{q}_{k}" for q, _ in PROFILI_BATT for k in
            ("ceduti_kwh", "eur", "scarica_kwh", "carica_ac_kwh", "perdite_kwh", "beneficio_eur")]


def main():
    os.makedirs(OUT, exist_ok=True)
    oggi = dt.datetime.now(ROMA).strftime("%Y-%m-%d")
    letture = letture_fv()
    giorni = sorted(g for g in letture if g < oggi)
    stato = {"scaricati": 0}
    righe, note = [], []
    soc = {q: 0.0 for q, _ in PROFILI_BATT}
    riporti = {q: [] for q, _ in PROFILI_BATT}
    os.makedirs(os.path.join(OUT, "giorni"), exist_ok=True)
    cache = {}

    def dati(g):
        if g not in cache:
            fv, cop = fv_quarti(g, letture[g])
            t0, nq = mezzanotte(g)
            pr, fonte = prezzi_giorno(g, nq, stato)
            cache[g] = (fv, cop, t0, nq, pr, fonte)
        return cache[g]

    for i, g in enumerate(giorni):
        fv, cop, t0, nq, prezzi, fonte = dati(g)
        if prezzi is None:
            note.append(f"{g}: {fonte}")
            soc = {q: 0.0 for q in soc}
            continue
        p0 = profilo0(fv, prezzi)
        dom = giorni[i + 1] if i + 1 < len(giorni) else None
        if dom and dom == (dt.date.fromisoformat(g) + dt.timedelta(days=1)).isoformat() and dati(dom)[4] is not None:
            fv2, pr2 = np.concatenate([fv, dati(dom)[0]]), np.concatenate([prezzi, dati(dom)[4]])
        else:
            fv2, pr2 = fv, prezzi
        try:
            ris = {q: profilo_batteria(fv2, pr2, soc[q], nq, ac) for q, ac in PROFILI_BATT}
        except Exception as e:
            note.append(f"{g}: {e}")
            continue
        riga = {"giorno": g, "mese": g[:7], "valido": int(cop >= COPERTURA_MINIMA), "copertura": round(cop, 3), "prezzi": fonte,
                "fv_kwh": round(fv.sum(), 3), "prezzo_medio_eur_kwh": round(float(prezzi.mean()), 5),
                "prezzo_min_eur_kwh": round(float(prezzi.min()), 5), "prezzo_max_eur_kwh": round(float(prezzi.max()), 5),
                "p0_ceduti_kwh": round(p0["ceduti_kwh"], 3), "p0_tagliati_kwh": round(p0["tagliati_kwh"], 3), "p0_eur": round(p0["eur"], 4)}
        for q, _ in PROFILI_BATT:
            x = ris[q]
            soc[q] = x["soc_fine_kwh"]
            riga.update({
                f"{q}_ceduti_kwh": round(x["ceduti_kwh"], 3), f"{q}_tagliati_kwh": round(x["tagliati_kwh"], 3), f"{q}_eur": round(x["eur"], 4),
                f"{q}_carica_kwh": round(x["carica_kwh"], 3), f"{q}_carica_ac_kwh": round(x["carica_ac_kwh"], 3),
                f"{q}_scarica_kwh": round(x["scarica_kwh"], 3), f"{q}_perdite_kwh": round(x["perdite_kwh"], 3),
                f"{q}_cicli": round(x["carica_kwh"] / CAPACITA_KWH, 3),
                f"{q}_prezzo_carica": "" if x["prezzo_carica"] is None else round(x["prezzo_carica"], 5),
                f"{q}_prezzo_scarica": "" if x["prezzo_scarica"] is None else round(x["prezzo_scarica"], 5),
                f"{q}_beneficio_eur": round(x["eur"] - p0["eur"], 4),
                f"{q}_energia_fine_kwh": round(x["soc_fine_kwh"], 3), f"{q}_riporto_eur": 0.0,
                f"{q}_prelievo_max_kwh": round(x["prelievo_max_kwh"], 6)})
            riporti[q].append((len(righe), x["soc_fine_kwh"], x["prezzo_scarica"]))
        righe.append(riga)
        with open(os.path.join(OUT, "giorni", f"{g}.json"), "w", encoding="utf-8") as fh:
            json.dump({"giorno": g, "inizio": t0, "profili": {q: ris[q]["quarti"] for q, _ in PROFILI_BATT}}, fh, separators=(",", ":"))
    # energia rimasta in batteria a mezzanotte: venduta il giorno dopo ma prodotta il giorno prima. Il suo valore
    # (kWh x (1 - perdita) x prezzo medio delle scariche del giorno dopo) passa al giorno della produzione: si somma
    # al giorno prima e si toglie al giorno dopo, cosi' il totale non cambia.
    for q, _ in PROFILI_BATT:
        rp = riporti[q]
        for j, (i, e_fine, pr_stesso) in enumerate(rp):
            if e_fine < 1e-6:
                continue
            succ = rp[j + 1] if j + 1 < len(rp) and rp[j + 1][0] == i + 1 else None
            pr = (succ[2] if succ and succ[2] is not None else None) or pr_stesso or righe[i]["prezzo_max_eur_kwh"]
            v = e_fine * (1 - PERDITA_CICLO) * pr
            for k, segno in ((i, 1), (succ[0], -1) if succ else (None, 0)):
                if k is None:
                    continue
                for col in (f"{q}_riporto_eur", f"{q}_eur", f"{q}_beneficio_eur"):
                    righe[k][col] = round(righe[k][col] + segno * v, 4)
    col = list(righe[0].keys()) if righe else ["giorno"]
    with open(os.path.join(OUT, "giornaliero.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=col)
        w.writeheader()
        w.writerows(righe)
    mesi = {}
    for r in righe:
        m = mesi.setdefault(r["mese"], {"mese": r["mese"], "giorni_validi": 0, "giorni_esclusi": 0, **{k: 0.0 for k in COL_MESE}})
        if not r["valido"]:
            m["giorni_esclusi"] += 1
            continue
        m["giorni_validi"] += 1
        for k in COL_MESE:
            m[k] += r[k]
    with open(os.path.join(OUT, "mensile.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["mese", "giorni_validi", "giorni_esclusi"] + COL_MESE)
        w.writeheader()
        for m in sorted(mesi):
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in mesi[m].items()})
    indice = {"aggiornato": dt.datetime.now(ROMA).isoformat(timespec="seconds"), "revisione": REVISIONE,
              "parametri": {"p_cismondi_kw": P_CISMONDI_KW, "p_impianto_kw": P_IMPIANTO_KW, "scala": round(SCALA, 5),
                            "limite_rete_kw": LIMITE_RETE_KW, "capacita_kwh": CAPACITA_KWH,
                            "potenza_batteria_kw": POTENZA_BATTERIA_KW, "p_inverter_kw": P_INVERTER_KW,
                            "quota_fv_a": QUOTA_FV_A, "perdita_ciclo": PERDITA_CICLO, "copertura_minima": COPERTURA_MINIMA},
              "giorni": len(righe), "note": note[-60:]}
    with open(os.path.join(OUT, "indice.json"), "w", encoding="utf-8") as fh:
        json.dump(indice, fh, ensure_ascii=False, indent=1)
    validi = [r for r in righe if r["valido"]]
    tot = lambda k: sum(r[k] for r in validi)
    testo = [f"# Cessione totale 20 kW - ultimo calcolo {dt.datetime.now(ROMA):%d/%m/%Y %H:%M} ({REVISIONE})", "",
             f"Giorni calcolati: {len(righe)} (validi {len(validi)}). Giorni senza prezzi o con errori: {len(note)}.", "",
             f"Profilo 0 (senza batteria): {tot('p0_ceduti_kwh'):.1f} kWh ceduti, {tot('p0_eur'):.2f} EUR",
             f"Profilo 1 (batteria {CAPACITA_KWH:g} kWh / {POTENZA_BATTERIA_KW:g} kW, senza carica AC): {tot('p1_ceduti_kwh'):.1f} kWh ceduti, "
             f"{tot('p1_eur'):.2f} EUR, beneficio {tot('p1_beneficio_eur'):.2f} EUR",
             f"Profilo 1AC (con carica AC dall'inverter B, mai dalla rete): {tot('p1ac_ceduti_kwh'):.1f} kWh ceduti, "
             f"{tot('p1ac_eur'):.2f} EUR, beneficio {tot('p1ac_beneficio_eur'):.2f} EUR (carica AC {tot('p1ac_carica_ac_kwh'):.1f} kWh)",
             ""] + [f"- {n}" for n in note[-60:]]
    with open(os.path.join(OUT, "ULTIMO_CALCOLO.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(testo) + "\n")
    log(f"{len(righe)} giorni ({len(validi)} validi), prezzi scaricati in questo giro: {stato['scaricati']}, "
        f"beneficio batteria: senza carica AC {tot('p1_beneficio_eur'):.2f} EUR, con carica AC {tot('p1ac_beneficio_eur'):.2f} EUR; "
        f"giorni non calcolati: {len(note)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:          # la simulazione principale non deve mai fermarsi per questa pagina
        print(f"Cessione totale: errore {ex}")
        sys.exit(0)
