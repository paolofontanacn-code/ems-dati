# -*- coding: utf-8 -*-
# Revisione R08 - 07/11/2026 - prima versione: rigioco della condizione 2 di Cismondi sui giorni prima della simulazione
"""
rigioco_c2.py - SOLO SIMULAZIONE: rigioca la condizione 2 (senza carica dalla rete) di Cismondi sui giorni dal primo
giorno di monitoraggio (12/09/2026) al giorno prima dell'avvio della simulazione vera, con le PREVISIONI che il sistema
avrebbe avuto (decisione dell'utente del 07/11/2026):
  - meteo previsto: archivio delle previsioni Open-Meteo (Historical Forecast API); se non risponde, meteo dello storico
    (misurato) e il giorno e' segnato;
  - consumi previsti: logica fuzzy (consumi_fuzzy.py) addestrata SOLO sui giorni prima, con la scelta automatica di
    inerzia e oblio sui 7 giorni prima;
  - produzione FV prevista: radiazione prevista x rendimento per ora del giorno imparato SOLO sui giorni prima;
  - prezzi NORD del GME (gia' scaricati per la cessione totale, altrimenti scaricati);
  - decisioni e batteria: mango/rigioco.lua (stesso ottimizzatore e stesso modello della batteria del Mango),
    decisione ogni ora; esecuzione dei quarti d'ora con i dati REALI.
I giorni si fanno in ordine (la batteria virtuale passa da un giorno all'altro; il primo giorno parte dal 50 %), qualche
giorno per giro, entro EMS_TEMPO_RIGIOCO secondi. Servono almeno 5 giorni prima per la logica fuzzy: i primi giorni
di monitoraggio servono solo come dati.
Uscite: rigioco/AAAA-MM-GG.json (quarti d'ora e totali), rigioco/giornaliero.csv, rigioco/stato.json
"""
import csv
import datetime as dt
import glob
import gzip
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import addestra as A  # noqa: E402
import consumi_fuzzy as FZ  # noqa: E402
import cessione_totale as CT  # noqa: E402

RADICE = A.RADICE
DATI = os.environ.get("EMS_DATI", os.path.join(RADICE, "memoria_mango"))
OUT = os.path.join(RADICE, "rigioco")
LUA = os.environ.get("EMS_LUA", "lua5.1")
TEMPO_S = float(os.environ.get("EMS_TEMPO_RIGIOCO", "300"))
MIN_GIORNI_PRIMA = 5
P_FV = 11000.0
URL_PREV = os.environ.get("EMS_PROVA_METEO_STORICO_PREV", "https://historical-forecast-api.open-meteo.com/v1/forecast")


def log(m):
    print(f"Rigioco condizione 2: {m}", flush=True)


def leggi_json(f, predef):
    try:
        with open(f, encoding="utf-8") as h:
            return json.load(h)
    except (OSError, ValueError):
        return predef


def scrivi_json(f, d):
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f + ".tmp", "w", encoding="utf-8") as h:
        json.dump(d, h, ensure_ascii=False)
    os.replace(f + ".tmp", f)


def contatore_quarti():
    """prelievo e immissione reali (W medi per quarto d'ora) dallo storico a 5 minuti"""
    righe = []
    for f in sorted(glob.glob(os.path.join(RADICE, "storico", "storico_*.csv*"))):
        righe.append(A.leggi_csv(f)[["ts", "contatore_w"]])
    if not righe:
        return {}
    d = pd.concat(righe).dropna().drop_duplicates("ts")
    d["tq"] = d["ts"].astype(np.int64) // 900 * 900
    m = d.groupby("tq")["contatore_w"].mean()
    return {int(t): float(v) for t, v in m.items()}


def meteo_previsto(giorno, lat, lon):
    """archivio delle previsioni Open-Meteo, ore UTC: {ts_ora: (temp, ghi, nuvole)}; None se non disponibile"""
    f = os.path.join(OUT, "meteo", f"prev_{giorno}.json")
    d = leggi_json(f, None)
    if d is None:
        g0 = (dt.date.fromisoformat(giorno) - dt.timedelta(days=1)).isoformat()
        g1 = (dt.date.fromisoformat(giorno) + dt.timedelta(days=1)).isoformat()
        q = {"latitude": lat, "longitude": lon, "start_date": g0, "end_date": g1, "timezone": "UTC", "timeformat": "unixtime",
             "hourly": "temperature_2m,shortwave_radiation,cloud_cover"}
        try:
            with urllib.request.urlopen(URL_PREV + "?" + urllib.parse.urlencode(q), timeout=30) as r:
                d = json.load(r)
            if not d.get("hourly", {}).get("time"):
                return None
            scrivi_json(f, d)
        except Exception as ex:                                   # noqa: BLE001
            log(f"meteo previsto del {giorno} non disponibile ({ex})")
            return None
    h = d["hourly"]
    return {int(t): (h["temperature_2m"][i], h["shortwave_radiation"][i], h["cloud_cover"][i]) for i, t in enumerate(h["time"])}


def con_meteo_previsto(x, mp):
    """sostituisce temperatura e radiazione dei quarti con quelle previste (stessa regola del Mango per la radiazione:
    media dell'ora che finisce dopo)"""
    x = x.copy()
    temp, ghi = [], []
    for t in x["ts"]:
        h0 = int(t) // 3600 * 3600
        a, b = mp.get(h0), mp.get(h0 + 3600)
        if a is None or b is None or a[0] is None or b[0] is None:
            temp.append(np.nan)
            ghi.append(np.nan)
            continue
        f = (int(t) + 450 - h0) / 3600
        temp.append(a[0] + (b[0] - a[0]) * f)
        ghi.append(b[1])
    x["temp"] = pd.Series(temp, index=x.index).interpolate(limit_direction="both")
    x["ghi"] = pd.Series(ghi, index=x.index).fillna(0)
    return x


def rendimento_fv(prima):
    """rapporto produzione / (radiazione x potenza) per ora del giorno, imparato sui soli giorni prima"""
    p = prima.dropna(subset=["fv_w", "ghi"])
    p = p[p["ghi"] > 50]
    k = np.clip(p["fv_w"] / (p["ghi"] / 1000 * P_FV), 0, 1.3)
    m = k.groupby(p["ora"]).median()
    return {int(h): float(v) for h, v in m.items()}


def quadro_giorno(giorno):
    t0 = int(pd.Timestamp(giorno).tz_localize(A.ROMA).timestamp())
    t1 = int(pd.Timestamp(dt.date.fromisoformat(giorno) + dt.timedelta(days=1)).tz_localize(A.ROMA).timestamp())
    x = A.aggiungi_calendario(pd.DataFrame({"ts": list(range(t0, t1, 900))}))
    return x, t0


def previsioni(df, giorno, lat, lon, cache_mod):
    """consumi e FV previsti (W) per i quarti del giorno, con i soli dati dei giorni prima"""
    d = dt.date.fromisoformat(giorno)
    x, t0 = quadro_giorno(giorno)
    # la "sera prima": i dati arrivano fino all'inizio del giorno precedente alle 21 (come la richiesta del Mango)
    prima = df[df["data"] < d]
    mp = meteo_previsto(giorno, lat, lon)
    fonte_meteo = "previsto (archivio Open-Meteo)"
    reale = df[df["data"] == d][["ts", "temp", "ghi"]]
    if mp:
        x = con_meteo_previsto(x, mp)
    else:
        x = x.merge(reale, on="ts", how="left")
        x["temp"] = x["temp"].interpolate(limit_direction="both")
        x["ghi"] = x["ghi"].fillna(0)
        fonte_meteo = "misurato (archivio delle previsioni non disponibile)"
    x["carico_w"] = np.nan
    chiave = str(d)
    if chiave not in cache_mod:
        g7 = sorted(prima["data"].unique())[-7:]
        migliore, _ = FZ.scegli(prima[~prima["data"].isin(g7)], prima[prima["data"].isin(g7)])
        cache_mod[chiave] = FZ.addestra(prima, migliore[1], migliore[2], migliore[3]) if migliore else FZ.addestra(prima, 12, 0.995)
    mod = cache_mod[chiave]
    if mod is None:
        return x, None, None, fonte_meteo, None
    pc = FZ.stima(mod, prima, x)
    k = rendimento_fv(prima)
    fv = [min(P_FV, k.get(int(o), 0.8) * g / 1000 * P_FV) for o, g in zip(x["ora"], x["ghi"])]
    return x, [pc.get(int(t), np.nan) for t in x["ts"]], fv, fonte_meteo, mod


def prezzi(giorno, nq, st_dl):
    pr, motivo = CT.prezzi_giorno(giorno, nq, st_dl)
    return (None if pr is None else [float(v) for v in pr]), motivo


def main():
    t_inizio = time.perf_counter()
    df = A.carica_dati()
    if df is None:
        log("nessun dato")
        return
    df = A.prepara(df)
    stato = leggi_json(os.path.join(OUT, "stato.json"), {}) or {}
    # giorni da rigiocare: storico (solo reale) fino al giorno prima dell'avvio della simulazione vera
    sim = sorted(os.path.basename(p) for p in glob.glob(os.path.join(RADICE, "dati", "20*")))
    avvio = sim[0] if sim else None
    tutti = sorted(str(g) for g in df["data"].unique())
    giorni = [g for g in tutti if avvio is None or g < avvio]
    giorni = giorni[MIN_GIORNI_PRIMA:]
    fatti = set(stato.get("fatti", []))
    da_fare = [g for g in giorni if g not in fatti]
    if not da_fare:
        log(f"niente da fare ({len(fatti)} giorni gia' rigiocati)")
        return
    lat, lon = CT.coordinate() or (None, None)
    if lat is None:
        log("coordinate non disponibili: rimando")
        return
    cont = contatore_quarti()
    reali = df.set_index("ts")
    st_dl, cache_mod = {"scaricati": 0}, {}
    soc0 = stato.get("soc_fine") or {"C2": 50.0, "auto": 50.0}
    for g in da_fare:
        if time.perf_counter() - t_inizio > TEMPO_S:
            break
        x, t0 = quadro_giorno(g)
        nq = len(x)
        nord, motivo = prezzi(g, nq, st_dl)
        if nord is None:
            log(f"{g}: prezzi non disponibili ({motivo}): mi fermo qui (i giorni vanno in ordine)")
            break
        reale_ok = [int(t) in reali.index and not np.isnan(reali.loc[int(t), "carico_w"]) and not np.isnan(reali.loc[int(t), "fv_w"])
                    for t in x["ts"]]
        if sum(reale_ok) < nq * 0.9:
            log(f"{g}: dati reali incompleti ({sum(reale_ok)}/{nq} quarti d'ora): giorno saltato, batteria ripresa dal giorno prima")
            stato.setdefault("saltati", []).append(g)
            fatti.add(g)
            continue
        xp, car_prev, fv_prev, fonte_meteo, _ = previsioni(df, g, lat, lon, cache_mod)
        if car_prev is None:
            log(f"{g}: pochi dati prima per la logica fuzzy (servono almeno 5 giorni completi): giorno saltato")
            stato.setdefault("saltati", []).append(g)
            fatti.add(g)
            continue
        # domani: previsioni e prezzi (la simulazione vera li conosce dalle 13 circa)
        g1 = (dt.date.fromisoformat(g) + dt.timedelta(days=1)).isoformat()
        domani = []
        x1, _ = quadro_giorno(g1)
        nord1, _ = prezzi(g1, len(x1), st_dl)
        if nord1 is not None and g1 in tutti:
            _, car1, fv1, _, _ = previsioni(df[df["data"] < dt.date.fromisoformat(g1)], g1, lat, lon, cache_mod)
            domani = [] if car1 is None else [{"t": int(t), "giorno": g1.replace("-", ""), "mezzanotte": k == 0, "fv_prev": float(fv1[k]),
                       "carico_prev": float(car1[k]) if not np.isnan(car1[k]) else 800.0, "nord": nord1[k]}
                      for k, t in enumerate(x1["ts"])]
        quarti = []
        for k, t in enumerate(x["ts"]):
            t = int(t)
            r = reali.loc[t] if t in reali.index else None
            quarti.append({"t": t, "giorno": g.replace("-", ""), "mezzanotte": k == 0,
                           "fv": float(r["fv_w"]) if r is not None and not np.isnan(r["fv_w"]) else 0.0,
                           "carico": float(r["carico_w"]) if r is not None and not np.isnan(r["carico_w"]) else 800.0,
                           "fv_prev": float(fv_prev[k]), "carico_prev": float(car_prev[k]) if not np.isnan(car_prev[k]) else 800.0,
                           "nord": nord[k]})
        ing = {"giorno": g.replace("-", ""), "soc0": soc0, "ora_prezzi_domani": 13, "quarti": quarti, "domani": domani,
               "modelli": os.path.join(DATI, "modelli.json")}
        f_in = os.path.join(OUT, "_ingresso.json")
        f_out = os.path.join(OUT, "_uscita.json")
        scrivi_json(f_in, ing)
        p = subprocess.run([LUA, os.path.join(RADICE, "mango", "rigioco.lua"), f_in, f_out], capture_output=True, text=True, timeout=600)
        if p.returncode != 0:
            log(f"{g}: errore del rigioco in Lua: {p.stderr.strip()[-300:]}")
            break
        res = leggi_json(f_out, None)
        # condizione 1: reale misurato dal contatore (senza usura: nello storico non c'e' la batteria)
        costo = res["costo_acquisto"]
        prel = sum(max(0.0, -cont.get(q["t"], 0.0)) for q in quarti) * 0.25 / 1000
        imm_eur = sum(max(0.0, cont.get(q["t"], 0.0)) * 0.25 / 1000 * q["nord"] for q in quarti)
        imm = sum(max(0.0, cont.get(q["t"], 0.0)) for q in quarti) * 0.25 / 1000
        tot = res["totali"]
        tot["c1_netto_eur"] = prel * costo - imm_eur
        tot["c1_prel_kwh"], tot["c1_imm_kwh"] = prel, imm
        uscita = {"giorno": g, "revisione": "R08", "meteo": fonte_meteo, "decisione": "ogni ora", "soc_inizio": soc0,
                  "mae_consumi_previsti_w": FZ.mae(car_prev, [q["carico"] for q in quarti]),
                  "quarti": [dict(r, fv_w=q["fv"], carico_w=q["carico"], fv_prev_w=q["fv_prev"], carico_prev_w=q["carico_prev"],
                                  nord=q["nord"]) for r, q in zip(res["quarti"], quarti)],
                  **{k: res[k] for k in ("soc_fine", "decisioni", "comandi", "finestre", "rendimenti", "costo_acquisto", "totali")}}
        scrivi_json(os.path.join(OUT, f"{g}.json"), uscita)
        soc0 = res["soc_fine"]
        fatti.add(g)
        stato.update({"fatti": sorted(fatti), "soc_fine": soc0, "ultimo": g})
        scrivi_json(os.path.join(OUT, "stato.json"), stato)
        log(f"{g}: condizione 2 {tot['c2_netto_eur']:.2f} EUR, automatico {tot['auto_netto_eur']:.2f} EUR, "
            f"senza batteria {tot['c0_netto_eur']:.2f} EUR, reale {tot['c1_netto_eur']:.2f} EUR (meteo {fonte_meteo})")
    for f in ("_ingresso.json", "_uscita.json"):
        try:
            os.remove(os.path.join(OUT, f))
        except OSError:
            pass
    stato.update({"fatti": sorted(fatti), "soc_fine": soc0, "revisione": "R08",
                  "aggiornato": dt.datetime.now(A.ROMA).isoformat(timespec="minutes")})
    scrivi_json(os.path.join(OUT, "stato.json"), stato)
    # riepilogo giornaliero
    righe = []
    for f in sorted(glob.glob(os.path.join(OUT, "20*.json"))):
        d = leggi_json(f, None)
        if not d:
            continue
        t = d["totali"]
        righe.append({"giorno": d["giorno"], "fv_kwh": round(t["fv_kwh"], 2), "carico_kwh": round(t["carico_kwh"], 2),
                      "c0_netto_eur": round(t["c0_netto_eur"], 3), "c1_netto_eur": round(t["c1_netto_eur"], 3),
                      "auto_netto_eur": round(t["auto_netto_eur"], 3), "c2_netto_eur": round(t["c2_netto_eur"], 3),
                      "c2_beneficio_vs_c1_eur": round(t["c1_netto_eur"] - t["c2_netto_eur"], 3),
                      "c2_beneficio_vs_auto_eur": round(t["auto_netto_eur"] - t["c2_netto_eur"], 3),
                      "c2_beneficio_vs_zero_eur": round(t["c0_netto_eur"] - t["c2_netto_eur"], 3),
                      "comandi": d["comandi"], "meteo": d["meteo"],
                      "mae_consumi_previsti_w": None if d.get("mae_consumi_previsti_w") is None else round(d["mae_consumi_previsti_w"], 1)})
    if righe:
        with open(os.path.join(OUT, "giornaliero.csv"), "w", encoding="utf-8", newline="") as h:
            w = csv.DictWriter(h, fieldnames=list(righe[0]))
            w.writeheader()
            w.writerows(righe)
    log(f"giorni rigiocati in tutto: {len(righe)} su {len(giorni)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:                                        # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"Rigioco condizione 2: errore {ex}")
        sys.exit(0)
