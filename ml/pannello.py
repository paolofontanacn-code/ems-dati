# -*- coding: utf-8 -*-
"""
pannello.py - prepara i file letti dalla pagina index.html (cartella pannello/).
Gira su GitHub a ogni giro, dopo la simulazione. Solo lettura dei dati: non tocca la simulazione.
  pannello/indice.json      elenco dei giorni, giorno in corso, piano, ultime righe del registro
  pannello/giornaliero.csv  totali giorno per giorno (storico importato + giorni simulati)
  pannello/oggi.csv         dati a 5 minuti del giorno in corso (non ancora chiuso; non compresso: git salva solo le differenze)
  pannello/oggi_periodi.csv periodi di carica/scarica del giorno in corso
  pannello/piano.csv        ultimo piano calcolato (giorno indicato in indice.json)
  pannello/piano_prezzi.json prezzi GME del giorno del piano
"""
import csv
import datetime as dt
import glob
import gzip
import json
import os
import shutil
from zoneinfo import ZoneInfo

ROMA = ZoneInfo("Europe/Rome")
DATI = os.environ.get("EMS_DATI", "memoria_mango")
OUT = "pannello"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def giorni_storico():
    """totali giornalieri dallo storico importato (letture a 5 minuti)"""
    tot = {}
    for f in sorted(glob.glob("storico/storico_*.csv.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                t = num(r.get("ts"))
                if t is None:
                    continue
                g = dt.datetime.fromtimestamp(t, ROMA).strftime("%Y-%m-%d")
                x = tot.setdefault(g, {"n": 0, "fv": 0.0, "car": 0.0, "prel": 0.0, "imm": 0.0})
                k = 300 / 3.6e6                      # W per 5 minuti -> kWh
                fv, car, cont = num(r.get("fv_w")) or 0, num(r.get("carico_w")) or 0, num(r.get("contatore_w")) or 0
                x["n"] += 1
                x["fv"] += fv * k
                x["car"] += car * k
                x["prel"] += max(0, -cont) * k
                x["imm"] += max(0, cont) * k
    return tot


def main():
    os.makedirs(OUT, exist_ok=True)
    ora = dt.datetime.now(ROMA)
    sim = sorted(os.path.basename(d) for d in glob.glob("dati/????-??-??") if os.path.isfile(os.path.join(d, "dataset.csv.gz")))
    sto = giorni_storico()

    # giorno in corso: l'ultimo dataset nella memoria non ancora chiuso in dati/
    oggi = None
    ds = sorted(glob.glob(os.path.join(DATI, "dataset_????????.csv")))
    if ds:
        g = os.path.basename(ds[-1])[8:16]
        g = f"{g[:4]}-{g[4:6]}-{g[6:]}"
        if g not in sim:
            oggi = g
            shutil.copyfile(ds[-1], os.path.join(OUT, "oggi.csv"))
            per = os.path.join(DATI, f"periodi_{g.replace('-', '')}.csv")
            if os.path.isfile(per):
                shutil.copyfile(per, os.path.join(OUT, "oggi_periodi.csv"))
            elif os.path.exists(os.path.join(OUT, "oggi_periodi.csv")):
                os.remove(os.path.join(OUT, "oggi_periodi.csv"))

    # ultimo piano calcolato
    piano = None
    ps = sorted(glob.glob(os.path.join(DATI, "piano_sera_????????.csv")))
    if ps:
        gp = os.path.basename(ps[-1])[11:19]
        piano = f"{gp[:4]}-{gp[4:6]}-{gp[6:]}"
        shutil.copyfile(ps[-1], os.path.join(OUT, "piano.csv"))
        pr = os.path.join(DATI, "prezzi", f"prezzi_{gp}.json")
        if os.path.isfile(pr):
            shutil.copyfile(pr, os.path.join(OUT, "piano_prezzi.json"))

    # totali giorno per giorno (riepilogo attuale + quello delle versioni precedenti, se c'e')
    riep, profili = {}, []
    # versioni precedenti (riepilogo_v1.csv, riepilogo_v<ora>.csv) in ordine di tempo, poi il riepilogo attuale
    vecchi = glob.glob(os.path.join(DATI, "riepilogo_v*.csv"))
    vecchi.sort(key=lambda f: (0, 0) if f.endswith("_v1.csv") else (1, int("".join(ch for ch in os.path.basename(f) if ch.isdigit()) or 0)))
    for f in vecchi + ["riepilogo.csv"]:
        if not os.path.isfile(f):
            continue
        with open(f, encoding="utf-8") as fh:
            lettore = csv.DictReader(fh)
            for k in lettore.fieldnames or []:
                if k.endswith("_beneficio_eur") and not k.endswith("_vs_zero_eur"):
                    p = k[:-len("_beneficio_eur")]
                    if p not in profili:
                        profili.append(p)
            for r in lettore:
                g = r.get("giorno") or ""
                if len(g) == 8:
                    riep[f"{g[:4]}-{g[4:6]}-{g[6:]}"] = r
    col = ["giorno", "tipo", "tipo_giorno", "fv_kwh", "carico_kwh", "prel_kwh", "imm_kwh", "zero_netto_eur", "c0_netto_eur", "c1_netto_eur",
           "reale_scarica_kwh"]
    for p in profili:
        col += [f"{p}_reale_netto_eur", f"{p}_auto_netto_eur", f"{p}_scenario_netto_eur", f"{p}_beneficio_eur",
                f"{p}_beneficio_vs_zero_eur", f"{p}_beneficio_vs_c1_eur", f"{p}_scarica_forzata_kwh"]
    righe = []
    for g in sorted(set(sto) | set(riep)):
        if g in riep:
            r = riep[g]
            x = {"giorno": g, "tipo": "simulato", "tipo_giorno": r.get("tipo_giorno"), "fv_kwh": r.get("fv_kwh"),
                 "carico_kwh": r.get("carico_kwh"), "prel_kwh": r.get("reale_prel_kwh"), "imm_kwh": r.get("reale_imm_kwh")}
            zc, zr = num(r.get("zero_costo_eur")), num(r.get("zero_ricavo_eur"))
            x["zero_netto_eur"] = None if zc is None else round(zc - (zr or 0), 4)
            for k in ("c0_netto_eur", "c1_netto_eur", "reale_scarica_kwh"):
                x[k] = r.get(k)
            for p in profili:
                if r.get(f"{p}_costo_eur") in (None, ""):
                    continue
                x[f"{p}_beneficio_eur"] = r.get(f"{p}_beneficio_eur")
                x[f"{p}_beneficio_vs_zero_eur"] = r.get(f"{p}_beneficio_vs_zero_eur")
                x[f"{p}_beneficio_vs_c1_eur"] = r.get(f"{p}_beneficio_vs_c1_eur")
                x[f"{p}_scarica_forzata_kwh"] = r.get(f"{p}_scarica_forzata_kwh")
                rc, rr = num(r.get(f"{p}_reale_costo_eur")), num(r.get(f"{p}_reale_ricavo_eur"))
                x[f"{p}_reale_netto_eur"] = None if rc is None else round(rc - (rr or 0), 4)
                ac, ar, au = (num(r.get(f"{p}_{k}")) for k in ("auto_costo_eur", "auto_ricavo_eur", "auto_usura_eur"))
                x[f"{p}_auto_netto_eur"] = None if ac is None else round(ac - (ar or 0) + (au or 0), 4)
                sc, sr, su, si = (num(r.get(f"{p}_{k}")) for k in ("costo_eur", "ricavo_eur", "usura_eur", "costo_interventi_eur"))
                x[f"{p}_scenario_netto_eur"] = None if sc is None else round(sc - (sr or 0) + (su or 0) + (si or 0), 4)
        else:
            s = sto[g]
            if s["n"] < 200:                  # giorno troppo incompleto
                continue
            x = {"giorno": g, "tipo": "storico", "fv_kwh": round(s["fv"], 3), "carico_kwh": round(s["car"], 3),
                 "prel_kwh": round(s["prel"], 3), "imm_kwh": round(s["imm"], 3)}
        righe.append(x)
    with open(os.path.join(OUT, "giornaliero.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=col, extrasaction="ignore")
        w.writeheader()
        for x in righe:
            w.writerow(x)

    registro = []
    log = os.path.join(DATI, "ems_sim.log")
    if os.path.isfile(log):
        with open(log, encoding="utf-8", errors="replace") as fh:
            registro = [x.rstrip("\n") for x in fh.readlines()[-80:]]

    giorni = [{"g": g, "tipo": "storico"} for g in sorted(sto) if g not in riep and g not in sim and sto[g]["n"] >= 200]
    giorni += [{"g": g, "tipo": "simulato"} for g in sim]
    if oggi:
        giorni.append({"g": oggi, "tipo": "oggi"})
    giorni.sort(key=lambda x: x["g"])
    diagnosi = []
    if os.path.isfile(os.path.join(OUT, "diagnosi_rete.txt")):
        with open(os.path.join(OUT, "diagnosi_rete.txt"), encoding="utf-8") as fh:
            diagnosi = [x.rstrip("\n") for x in fh]
    indice = {"aggiornato": ora.isoformat(timespec="seconds"), "giorni": giorni, "oggi": oggi, "piano": piano,
              "diagnosi_rete": diagnosi,
              "mesi_storico": sorted(os.path.basename(f)[8:14] for f in glob.glob("storico/storico_*.csv.gz")),
              "registro": registro}
    with open(os.path.join(OUT, "indice.json"), "w", encoding="utf-8") as fh:
        json.dump(indice, fh, ensure_ascii=False, indent=1)
    print(f"Pannello: {len(sim)} giorni simulati, {len(giorni) - len(sim) - (1 if oggi else 0)} giorni di storico, "
          f"in corso {oggi or '-'}, piano {piano or '-'}")


if __name__ == "__main__":
    main()
