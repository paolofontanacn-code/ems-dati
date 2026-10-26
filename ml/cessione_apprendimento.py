# -*- coding: utf-8 -*-
# Revisione R05 - 26/10/2026 - il rigioco applica anche la regola di stabilita' e la potenza TOU del piano
# Revisione R04 - 24/10/2026 - prima versione: autoapprendimento con algoritmo evolutivo, rigiocando i giorni vissuti
"""
cessione_apprendimento.py - SOLO SIMULAZIONE: autoapprendimento della simulazione ogni 2 ore della cessione totale.
Gira su GitHub in un workflow separato (ogni 2 ore, fino a circa 45 minuti di calcolo) per non bloccare il giro dei 30 minuti.

Cosa fa:
 1. prende le decisioni delle ultime 2 settimane con il CONTESTO di allora (previsione di produzione, incertezza, prezzi
    noti e previsti, salvati in cessione/live/contesti/) e la produzione e i prezzi VERI di quei quarti d'ora;
 2. RIGIOCA tutte quelle decisioni con un insieme di parametri (theta: valore dell'energia lasciata in batteria,
    ampiezza e peso degli scenari di produzione, costo dei cambi di modalita', regole fuzzy), con lo stesso algoritmo
    evolutivo della decisione, e misura il ricavo che si sarebbe ottenuto davvero;
 3. cerca parametri migliori con un algoritmo evolutivo sui parametri (mutazioni del migliore trovato);
 4. ADOTTA i nuovi parametri solo se sugli stessi giorni avrebbero reso di piu' dei parametri in uso.
Uscita: cessione/live/apprendimento.json (parametri in uso e storico delle prove).
"""
import datetime as dt
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cessione_totale as CT  # noqa: E402
import cessione_ottimizza as CO  # noqa: E402

LIVE = os.path.join(CT.OUT, "live")
TEMPO_S = float(os.environ.get("EMS_TEMPO_APPRENDIMENTO", "2700"))
GIORNI = 14
POP_RIGIOCO, GEN_RIGIOCO = 60, 40          # ricerca piu' corta della decisione vera (stessa per tutti i parametri)
MIN_CONTESTI = 6


def log(msg):
    print(f"Cessione apprendimento: {msg}", flush=True)


def carica(f, predef):
    try:
        return json.load(open(f, encoding="utf-8"))
    except (OSError, ValueError):
        return predef


def dati():
    """contesti delle ultime 2 settimane e quarti d'ora veri {t: (produzione, prezzo)}"""
    limite = float(os.environ.get("EMS_ORA_REALE") or time.time()) - GIORNI * 86400
    contesti = []
    for f in glob.glob(os.path.join(LIVE, "contesti", "*.json")):
        c = carica(f, None)
        if c and c.get("t_dati", 0) >= limite:
            contesti.append(c)
    contesti.sort(key=lambda c: c["t_dati"])
    veri = {}
    for f in glob.glob(os.path.join(LIVE, "giorni", "*.json")):
        for q in (carica(f, {}) or {}).get("quarti", []):
            veri[int(q["t"])] = (float(q["fv"]), float(q["prezzo"]))
    # ogni contesto vale fino al successivo; si tengono solo i tratti con tutti i quarti veri
    tratti = []
    for i, c in enumerate(contesti):
        fine = contesti[i + 1]["t_dati"] if i + 1 < len(contesti) else (max(veri) + 900 if veri else c["t_dati"])
        qs = list(range(int(c["t_dati"]), int(fine), 900))
        if qs and all(t in veri for t in qs):
            tratti.append((c, qs))
    return tratti, veri


def rigioca(theta, tratti, veri):
    """ricavo vero (EUR) che i parametri theta avrebbero ottenuto sugli stessi giorni"""
    soc, eur, prec, t_atteso = None, 0.0, None, None
    for c, qs in tratti:
        if soc is None or c["t_dati"] != t_atteso:                 # inizio o buco: si riparte dall'energia vera di allora
            soc, prec = float(c["soc"]), None
        ctx = dict(c, soc=soc)
        r = CO.decidi(ctx, theta, tempo_s=1e9, pop=POP_RIGIOCO, max_gen=GEN_RIGIOCO, stallo=GEN_RIGIOCO,
                      seme=int(c["t_dati"]) % 100000, precedente=prec)
        piano, _ = CO.stabilita(ctx, theta, r["piano"], prec)
        for t in qs:
            voce = piano.get(str(t), [0, 0.0])
            pv, pr = veri[t]
            _, _, ced, _, soc = CO.esegui_quarto(voce[0], voce[1], pv, soc, voce[2] if len(voce) > 2 else CO.P_CMD_KW)
            eur += ced * pr
        prec, t_atteso = piano, qs[-1] + 900
    media = float(np.mean([veri[t][1] for _, qs in tratti for t in qs])) if tratti else 0.0
    return eur + (soc or 0.0) * CO.ETA_D * media                   # energia rimasta valutata al prezzo medio


def muta(theta, rng, forza):
    nuovo = dict(theta)
    for k, (a, b) in CO.LIMITI_THETA.items():
        if rng.random() < 0.6:
            nuovo[k] = float(np.clip(theta[k] + rng.normal(0, forza * (b - a)), a, b))
    if nuovo["fz_alto"] <= nuovo["fz_basso"] + 0.05:
        nuovo["fz_alto"] = min(0.95, nuovo["fz_basso"] + 0.1)
    return nuovo


def main():
    t0 = time.perf_counter()
    tratti, veri = dati()
    fapp = os.path.join(LIVE, "apprendimento.json")
    stato = carica(fapp, {}) or {}
    if len(tratti) < MIN_CONTESTI:
        log(f"dati ancora pochi ({len(tratti)} decisioni con i quarti d'ora veri, ne servono {MIN_CONTESTI}): niente da imparare per ora")
        return
    theta = CO.carica_theta()
    rng = np.random.default_rng(int(time.time()) % 2 ** 31)
    base = rigioca(theta, tratti, veri)
    durata = time.perf_counter() - t0
    log(f"{len(tratti)} decisioni rigiocate in {durata:.0f} s: ricavo con i parametri in uso {base:.2f} EUR")
    migliore, theta_m, provati = base, dict(theta), []
    forza = 0.15
    while time.perf_counter() - t0 + durata * 1.2 < TEMPO_S:
        cand = muta(theta_m, rng, forza)
        v = rigioca(cand, tratti, veri)
        provati.append({"theta": {k: round(x, 4) for k, x in cand.items()}, "eur": round(v, 3)})
        if v > migliore + 1e-6:
            migliore, theta_m = v, cand
            forza = min(0.25, forza * 1.2)
        else:
            forza = max(0.03, forza * 0.95)
    adottato = migliore > base + max(0.02, 0.001 * abs(base))
    if adottato:
        stato["theta"] = {k: round(x, 4) for k, x in theta_m.items()}
    storico = (stato.get("storico") or [])[-200:]
    storico.append({"quando": dt.datetime.now(CT.ROMA).isoformat(timespec="minutes"), "decisioni": len(tratti),
                    "eur_parametri_in_uso": round(base, 3), "eur_migliore_trovato": round(migliore, 3), "adottato": adottato,
                    "parametri_provati": len(provati), "secondi": round(time.perf_counter() - t0)})
    stato.update({"revisione": CT.REVISIONE, "aggiornato": dt.datetime.now(CT.ROMA).isoformat(timespec="seconds"),
                  "theta": stato.get("theta") or {k: round(x, 4) for k, x in theta.items()}, "storico": storico,
                  "ultimi_provati": sorted(provati, key=lambda x: -x["eur"])[:20]})
    os.makedirs(LIVE, exist_ok=True)
    with open(fapp + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(stato, fh, ensure_ascii=False, indent=1)
    os.replace(fapp + ".tmp", fapp)
    log(f"provati {len(provati)} insiemi di parametri; migliore {migliore:.2f} EUR contro {base:.2f} EUR in uso: "
        + ("ADOTTATO" if adottato else "non adottato (non rende di piu')"))


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"Cessione apprendimento: errore {ex}")
        sys.exit(0)
