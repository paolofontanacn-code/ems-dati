# -*- coding: utf-8 -*-
"""
cessione_totale.py - SOLO SIMULAZIONE: impianto FV da 20 kW in cessione totale (tutto il prodotto va in rete, RID).

Produzione: letture Huawei a 5 minuti dell'impianto di Cismondi (11,48 kW, inclinazione simile) x 20 / 11,48.
  - giorni prima dell'avvio della simulazione: storico/storico_AAAAMM.csv.gz
  - giorni simulati (chiusi): dati/AAAA-MM-GG/dataset.csv.gz
Prezzi: oggi l'impianto vende in RID al prezzo orario (PO) zonale NORD: si usano i prezzi ORARI NORD del GME (MGP).
  - dati/AAAA-MM-GG/prezzi.json (gia' scaricati dalla simulazione) oppure scaricati dal GME e salvati in
    cessione/prezzi/prezzi_AAAAMMGG.json (una volta sola per giorno).
Profili:
  0 = senza batteria: ceduto = prodotto, al massimo LIMITE_RETE_KW (il resto si perde)
  1 = con batteria (CAPACITA_KWH, POTENZA_BATTERIA_KW), carica SOLO dal FV (nessuna carica da AC):
      ogni giorno, con i prezzi del giorno, la batteria immagazzina nei quarti d'ora a prezzo di cessione piu'
      basso e restituisce in quelli a prezzo piu' alto (programmazione lineare, massimo ricavo del giorno).
      Perdita tra carica e scarica: PERDITA_CICLO (5 %). Usura della batteria NON conteggiata.
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
CAPACITA_KWH = 30.0              # batteria del profilo 1 (capacita' utile)
POTENZA_BATTERIA_KW = 10.0       # potenza massima di carica e di scarica
PERDITA_CICLO = 0.05             # 5 % di perdita tra energia caricata ed energia restituita
COPERTURA_MINIMA = 0.90          # giorni con meno del 90 % delle letture: mostrati ma esclusi dai totali
SCALA = P_IMPIANTO_KW / P_CISMONDI_KW
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
    lim = LIMITE_RETE_KW * 0.25
    ceduto = np.minimum(fv, lim)
    return {"ceduti_kwh": ceduto.sum(), "tagliati_kwh": (fv - ceduto).sum(), "eur": float((ceduto * prezzi).sum())}


def profilo1(fv, prezzi, soc0, n_oggi=None):
    """programmazione lineare sul giorno e, se noto, sul giorno dopo (i prezzi del giorno dopo si conoscono dalle
    13 circa del giorno prima): si tengono solo le decisioni del giorno (orizzonte mobile). Variabili per quarto: c = carica dal FV, s = scarica (energia
    consegnata in rete), x = FV tagliato. Ceduto = fv - c - x + s <= limite. Energia in batteria:
    soc0 + somma(c) - somma(s) / (1 - perdita), tra 0 e la capacita'."""
    n = len(fv)
    lim, pb, eta = LIMITE_RETE_KW * 0.25, POTENZA_BATTERIA_KW * 0.25, 1 - PERDITA_CICLO
    # ricavo = somma p (fv - c - x + s): si minimizza  p.c + p.x - p.s
    costo = np.concatenate([prezzi, -prezzi, prezzi])
    L = np.tril(np.ones((n, n)))
    A, b = [], []
    # ceduto <= limite:  -c + s - x <= lim - fv
    A.append(np.hstack([-np.eye(n), np.eye(n), -np.eye(n)])); b.append(lim - fv)
    # c + x <= fv (si carica e si taglia solo FV)
    A.append(np.hstack([np.eye(n), np.zeros((n, n)), np.eye(n)])); b.append(fv)
    # energia in batteria <= capacita':  L c - L s / eta <= cap - soc0
    A.append(np.hstack([L, -L / eta, np.zeros((n, n))])); b.append(np.full(n, CAPACITA_KWH - soc0))
    # energia in batteria >= 0:  -L c + L s / eta <= soc0
    A.append(np.hstack([-L, L / eta, np.zeros((n, n))])); b.append(np.full(n, soc0))
    lim_var = [(0, pb)] * n + [(0, pb)] * n + [(0, None)] * n
    r = linprog(costo, A_ub=np.vstack(A), b_ub=np.concatenate(b), bounds=lim_var, method="highs")
    if r.status != 0:
        raise RuntimeError(f"ottimizzazione non riuscita: {r.message}")
    c, s, x = r.x[:n], r.x[n:2 * n], r.x[2 * n:]
    c[c < 1e-9], s[s < 1e-9], x[x < 1e-9] = 0, 0, 0
    m = n_oggi or n
    fv, prezzi, c, s, x = fv[:m], prezzi[:m], c[:m], s[:m], x[:m]
    ceduto = fv - c - x + s
    soc = soc0 + np.cumsum(c) - np.cumsum(s) / eta
    return {"ceduti_kwh": ceduto.sum(), "tagliati_kwh": x.sum(), "eur": float((ceduto * prezzi).sum()),
            "carica_kwh": c.sum(), "scarica_kwh": s.sum(), "perdite_kwh": s.sum() / eta - s.sum(),
            "soc_fine_kwh": float(soc[-1]), "soc_max_kwh": float(soc.max()),
            "prezzo_carica": float((c * prezzi).sum() / c.sum()) if c.sum() > 1e-6 else None,
            "prezzo_scarica": float((s * prezzi).sum() / s.sum()) if s.sum() > 1e-6 else None,
            "quarti": [{"fv": round(float(fv[k]), 4), "prezzo": round(float(prezzi[k]), 5), "carica": round(float(c[k]), 4),
                        "scarica": round(float(s[k]), 4), "tagliato": round(float(x[k]), 4), "soc": round(float(soc[k]), 3)}
                       for k in range(m)]}


# ------------------------------------------------------------------ principale
def main():
    os.makedirs(OUT, exist_ok=True)
    oggi = dt.datetime.now(ROMA).strftime("%Y-%m-%d")
    letture = letture_fv()
    giorni = sorted(g for g in letture if g < oggi)
    stato = {"scaricati": 0}
    righe, note, soc, riporti = [], [], 0.0, []
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
            soc = 0.0
            continue
        p0 = profilo0(fv, prezzi)
        dom = giorni[i + 1] if i + 1 < len(giorni) else None
        if dom and dom == (dt.date.fromisoformat(g) + dt.timedelta(days=1)).isoformat() and dati(dom)[4] is not None:
            fv2, pr2 = np.concatenate([fv, dati(dom)[0]]), np.concatenate([prezzi, dati(dom)[4]])
        else:
            fv2, pr2 = fv, prezzi
        try:
            p1 = profilo1(fv2, pr2, soc, nq)
        except Exception as e:
            note.append(f"{g}: {e}")
            continue
        soc = p1["soc_fine_kwh"]
        valido = cop >= COPERTURA_MINIMA
        righe.append({
            "giorno": g, "mese": g[:7], "valido": int(valido), "copertura": round(cop, 3), "prezzi": fonte,
            "fv_kwh": round(fv.sum(), 3), "prezzo_medio_eur_kwh": round(float(prezzi.mean()), 5),
            "prezzo_min_eur_kwh": round(float(prezzi.min()), 5), "prezzo_max_eur_kwh": round(float(prezzi.max()), 5),
            "p0_ceduti_kwh": round(p0["ceduti_kwh"], 3), "p0_tagliati_kwh": round(p0["tagliati_kwh"], 3), "p0_eur": round(p0["eur"], 4),
            "p1_ceduti_kwh": round(p1["ceduti_kwh"], 3), "p1_tagliati_kwh": round(p1["tagliati_kwh"], 3), "p1_eur": round(p1["eur"], 4),
            "p1_carica_kwh": round(p1["carica_kwh"], 3), "p1_scarica_kwh": round(p1["scarica_kwh"], 3),
            "p1_perdite_kwh": round(p1["perdite_kwh"], 3), "p1_cicli": round(p1["carica_kwh"] / CAPACITA_KWH, 3),
            "p1_prezzo_carica": "" if p1["prezzo_carica"] is None else round(p1["prezzo_carica"], 5),
            "p1_prezzo_scarica": "" if p1["prezzo_scarica"] is None else round(p1["prezzo_scarica"], 5),
            "beneficio_eur": round(p1["eur"] - p0["eur"], 4),
            "p1_energia_fine_kwh": round(p1["soc_fine_kwh"], 3), "p1_riporto_eur": 0.0,
        })
        riporti.append((len(righe) - 1, p1["soc_fine_kwh"], p1["prezzo_scarica"]))
        with open(os.path.join(OUT, "giorni", f"{g}.json"), "w", encoding="utf-8") as fh:
            json.dump({"giorno": g, "inizio": t0, "quarti": p1["quarti"]}, fh, separators=(",", ":"))
    # energia rimasta in batteria a mezzanotte: venduta il giorno dopo ma prodotta (e immagazzinata) il giorno prima.
    # Il suo valore (kWh x (1 - perdita) x prezzo medio delle scariche del giorno dopo) passa al giorno della
    # produzione: si somma al giorno prima e si toglie al giorno dopo, cosi' il totale non cambia.
    for j, (i, e_fine, pr_stesso) in enumerate(riporti):
        if e_fine < 1e-6:
            continue
        succ = riporti[j + 1] if j + 1 < len(riporti) and riporti[j + 1][0] == i + 1 else None
        pr = (succ[2] if succ and succ[2] is not None else None) or pr_stesso or righe[i]["prezzo_max_eur_kwh"]
        v = e_fine * (1 - PERDITA_CICLO) * pr
        righe[i]["p1_riporto_eur"] = round(righe[i]["p1_riporto_eur"] + v, 4)
        righe[i]["p1_eur"] = round(righe[i]["p1_eur"] + v, 4)
        righe[i]["beneficio_eur"] = round(righe[i]["beneficio_eur"] + v, 4)
        if succ:
            k = succ[0]
            righe[k]["p1_riporto_eur"] = round(righe[k]["p1_riporto_eur"] - v, 4)
            righe[k]["p1_eur"] = round(righe[k]["p1_eur"] - v, 4)
            righe[k]["beneficio_eur"] = round(righe[k]["beneficio_eur"] - v, 4)
    col = list(righe[0].keys()) if righe else ["giorno"]
    with open(os.path.join(OUT, "giornaliero.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=col)
        w.writeheader()
        w.writerows(righe)
    mesi = {}
    for r in righe:
        m = mesi.setdefault(r["mese"], {"mese": r["mese"], "giorni_validi": 0, "giorni_esclusi": 0, "fv_kwh": 0.0,
                                        "p0_ceduti_kwh": 0.0, "p0_eur": 0.0, "p1_ceduti_kwh": 0.0, "p1_eur": 0.0,
                                        "p1_scarica_kwh": 0.0, "p1_perdite_kwh": 0.0, "beneficio_eur": 0.0})
        if not r["valido"]:
            m["giorni_esclusi"] += 1
            continue
        m["giorni_validi"] += 1
        for k in ("fv_kwh", "p0_ceduti_kwh", "p0_eur", "p1_ceduti_kwh", "p1_eur", "p1_scarica_kwh", "p1_perdite_kwh", "beneficio_eur"):
            m[k] += r[k]
    with open(os.path.join(OUT, "mensile.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["mese", "giorni_validi", "giorni_esclusi", "fv_kwh", "p0_ceduti_kwh", "p0_eur",
                                           "p1_ceduti_kwh", "p1_eur", "p1_scarica_kwh", "p1_perdite_kwh", "beneficio_eur"])
        w.writeheader()
        for m in sorted(mesi):
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in mesi[m].items()})
    indice = {"aggiornato": dt.datetime.now(ROMA).isoformat(timespec="seconds"),
              "parametri": {"p_cismondi_kw": P_CISMONDI_KW, "p_impianto_kw": P_IMPIANTO_KW, "scala": round(SCALA, 5),
                            "limite_rete_kw": LIMITE_RETE_KW, "capacita_kwh": CAPACITA_KWH,
                            "potenza_batteria_kw": POTENZA_BATTERIA_KW, "perdita_ciclo": PERDITA_CICLO,
                            "copertura_minima": COPERTURA_MINIMA},
              "giorni": len(righe), "note": note[-60:]}
    with open(os.path.join(OUT, "indice.json"), "w", encoding="utf-8") as fh:
        json.dump(indice, fh, ensure_ascii=False, indent=1)
    validi = [r for r in righe if r["valido"]]
    tot = lambda k: sum(r[k] for r in validi)
    testo = [f"# Cessione totale 20 kW - ultimo calcolo {dt.datetime.now(ROMA):%d/%m/%Y %H:%M}", "",
             f"Giorni calcolati: {len(righe)} (validi {len(validi)}). Giorni senza prezzi o con errori: {len(note)}.", "",
             f"Profilo 0 (senza batteria): {tot('p0_ceduti_kwh'):.1f} kWh ceduti, {tot('p0_eur'):.2f} EUR",
             f"Profilo 1 (batteria {CAPACITA_KWH:g} kWh / {POTENZA_BATTERIA_KW:g} kW): {tot('p1_ceduti_kwh'):.1f} kWh ceduti, {tot('p1_eur'):.2f} EUR",
             f"Beneficio della batteria: {tot('beneficio_eur'):.2f} EUR", ""] + [f"- {n}" for n in note[-60:]]
    with open(os.path.join(OUT, "ULTIMO_CALCOLO.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(testo) + "\n")
    log(f"{len(righe)} giorni ({len(validi)} validi), prezzi scaricati in questo giro: {stato['scaricati']}, "
        f"beneficio batteria {tot('beneficio_eur'):.2f} EUR; giorni non calcolati: {len(note)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:          # la simulazione principale non deve mai fermarsi per questa pagina
        print(f"Cessione totale: errore {ex}")
        sys.exit(0)
