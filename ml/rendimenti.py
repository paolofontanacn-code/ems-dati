# -*- coding: utf-8 -*-
# Revisione R10 - 12/11/2026 - nuovo: rendimenti della batteria di Cismondi per fascia di potenza e pesi della potenza
"""
rendimenti.py - SOLO SIMULAZIONE: misura i rendimenti della batteria vera di Cismondi (LUNA2000 15 kWh) per fascia di
potenza e ne ricava i PESI DELLA POTENZA usati per scegliere i piani (Cismondi e cessione totale).

Dati: dati/AAAA-MM-GG/dataset.csv.gz (letture a 5 minuti: batteria_w, soc, eta_inv_*), dal 17/10/2026.
Tratto = letture consecutive (al massimo 10 minuti tra una e l'altra) con la batteria sempre in carica (o sempre in
  scarica) nella stessa fascia di potenza. Fasce (potenza / potenza massima 5 kW): 1 = fino all'80 %, 2 = oltre
  l'80 % fino al 90 %, 3 = oltre il 90 %.
Rendimento del tratto: carica = energia immagazzinata (variazione del SOC x 15 kWh) / energia entrata;
  scarica = energia uscita / energia tolta (variazione del SOC x 15 kWh). Si contano solo i tratti con almeno
  1,5 kWh (10 % di SOC): il SOC e' letto a passi dell'1 % (0,15 kWh).
Fascia VALIDA (decisione dell'utente 12/11/2026): almeno 10 tratti. Rendimento della fascia = somma delle energie.
Pesi (decisione 12/11/2026): peso della fascia valida = rendimento della fascia / miglior rendimento delle fasce
  valide (la migliore = 1); fascia non valida = peso fisso (1 / 0,98 / 0,97).
Rendimento dell'inverter (cessione, perdite di conversione): ultimo valore misurato dal Mango (colonne eta_inv_500,
  eta_inv_1000, eta_inv_2000, eta_inv_oltre del dataset).
Uscita: modelli/rendimenti_batteria.json (letto da mango/ems_sim.lua, mango/rigioco.lua, ml/cessione_ottimizza.py,
  ml/cessione_live.py e dalla pagina rendimenti.html).
"""
import datetime as dt
import glob
import json
import os

import pandas as pd

RADICE = os.environ.get("EMS_REPO_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
USCITA = os.path.join(RADICE, "modelli", "rendimenti_batteria.json")
REVISIONE = "R10"

CAPACITA_KWH = 15.0
P_MAX_W = 5000.0                       # carica e scarica massima della LUNA2000 di Cismondi
SOGLIE = (0.80, 0.90)
PESI_FISSI = (1.0, 0.98, 0.97)
P_MIN_W = 100.0                        # sotto: batteria considerata ferma
BUCO_MAX_S = 600
KWH_MIN_TRATTO = 1.5                   # 10 % di SOC
TRATTI_MIN = 10
ETA_INV_FISSO = 0.97                   # config.lua RENDIMENTO_INVERTER


def fascia(p):
    f = abs(p) / P_MAX_W
    return 1 if f <= SOGLIE[0] + 1e-9 else (2 if f <= SOGLIE[1] + 1e-9 else 3)


def leggi():
    parti = []
    for f in sorted(glob.glob(os.path.join(RADICE, "dati", "*", "dataset.csv.gz"))):
        try:
            d = pd.read_csv(f, usecols=lambda c: c in ("ts", "batteria_w", "soc", "eta_inv_500", "eta_inv_1000",
                                                       "eta_inv_2000", "eta_inv_oltre"))
        except Exception:
            continue
        if {"ts", "batteria_w", "soc"} <= set(d.columns):
            parti.append(d)
    if not parti:
        return None
    d = pd.concat(parti, ignore_index=True)
    d = d.dropna(subset=["ts", "batteria_w", "soc"]).sort_values("ts").drop_duplicates("ts")
    return d.reset_index(drop=True)


def tratti(d):
    """elenco dei tratti: tipo, fascia, inizio, fine, kWh di energia, kWh di SOC, rendimento"""
    out = []
    ts, pw, soc = d["ts"].to_numpy(float), d["batteria_w"].to_numpy(float), d["soc"].to_numpy(float)
    i, n = 1, len(d)
    while i < n:
        p = pw[i]
        if abs(p) < P_MIN_W or ts[i] - ts[i - 1] > BUCO_MAX_S:
            i += 1
            continue
        tipo, fa = ("carica" if p > 0 else "scarica"), fascia(p)
        j, e = i, 0.0
        while j < n and abs(pw[j]) >= P_MIN_W and (pw[j] > 0) == (p > 0) and fascia(pw[j]) == fa \
                and ts[j] - ts[j - 1] <= BUCO_MAX_S:
            e += abs(pw[j]) * (ts[j] - ts[j - 1]) / 3600 / 1000          # potenza media dell'intervallo che finisce in j
            j += 1
        dsoc = float(soc[j - 1] - soc[i - 1]) / 100 * CAPACITA_KWH
        e = float(e)
        eta = None
        if tipo == "carica" and e > 0 and dsoc > 0:
            eta = dsoc / e
        elif tipo == "scarica" and dsoc < 0:
            eta = e / -dsoc
        out.append({"tipo": tipo, "fascia": fa, "inizio": int(ts[i - 1]), "fine": int(ts[j - 1]), "kwh": round(e, 3),
                    "kwh_soc": round(abs(dsoc), 3), "eta": round(eta, 4) if eta else None,
                    "p_media_w": round(e * 1000 * 3600 / max(1.0, ts[j - 1] - ts[i - 1]), 0),
                    "usato": bool(eta and e >= KWH_MIN_TRATTO and 0.5 < eta < 1.1)})
        i = j
    return out


def riepilogo(tr, tipo):
    bande = []
    for fa in (1, 2, 3):
        u = [t for t in tr if t["tipo"] == tipo and t["fascia"] == fa and t["usato"]]
        tutti = [t for t in tr if t["tipo"] == tipo and t["fascia"] == fa]
        num = sum(t["kwh_soc"] if tipo == "carica" else t["kwh"] for t in u)
        den = sum(t["kwh"] if tipo == "carica" else t["kwh_soc"] for t in u)
        eta = num / den if den > 0 else None
        da = 0 if fa == 1 else SOGLIE[fa - 2]
        a = SOGLIE[fa - 1] if fa < 3 else 1.0
        bande.append({"fascia": fa, "da_perc": round(da * 100), "a_perc": round(a * 100), "da_w": round(da * P_MAX_W),
                      "a_w": round(a * P_MAX_W), "tratti": len(u), "tratti_totali": len(tutti),
                      "kwh": round(sum(t["kwh"] for t in u), 2), "eta": round(eta, 4) if eta else None,
                      "valida": len(u) >= TRATTI_MIN and eta is not None})
    valide = [b["eta"] for b in bande if b["valida"]]
    migliore = max(valide) if valide else None
    for b in bande:
        if b["valida"]:
            b["peso"], b["fonte_peso"] = float(round(b["eta"] / migliore, 4)), "misurato"
        else:
            b["peso"], b["fonte_peso"] = PESI_FISSI[b["fascia"] - 1], "fisso"
    return bande


def inverter(d):
    col = ["eta_inv_500", "eta_inv_1000", "eta_inv_2000", "eta_inv_oltre"]
    if d is not None and all(c in d.columns for c in col):
        u = d.dropna(subset=col)
        if len(u):
            v = [float(x) for x in u.iloc[-1][col]]
            return {"fasce_w": [500, 1000, 2000], "eta": [round(x, 4) for x in v], "fonte": "misurato dal Mango (ultimo valore)"}
    return {"fasce_w": [500, 1000, 2000], "eta": [ETA_INV_FISSO] * 4, "fonte": "ipotesi (config.lua)"}


def main():
    d = leggi()
    tr = tratti(d) if d is not None else []
    car, sca = riepilogo(tr, "carica"), riepilogo(tr, "scarica")
    ris = {
        "aggiornato": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="minutes"), "revisione": REVISIONE,
        "regole": {"capacita_kwh": CAPACITA_KWH, "p_max_w": P_MAX_W, "soglie": list(SOGLIE), "pesi_fissi": list(PESI_FISSI),
                   "kwh_min_tratto": KWH_MIN_TRATTO, "tratti_min": TRATTI_MIN, "p_min_w": P_MIN_W},
        "periodo": {"da": int(d["ts"].min()), "a": int(d["ts"].max()), "letture": int(len(d))} if d is not None else None,
        "carica": car, "scarica": sca,
        "pesi": {"carica": [b["peso"] for b in car], "scarica": [b["peso"] for b in sca]},
        "inverter": inverter(d),
        "tratti": tr[-400:],
    }
    os.makedirs(os.path.dirname(USCITA), exist_ok=True)
    with open(USCITA, "w", encoding="utf-8") as fh:
        json.dump(ris, fh, ensure_ascii=False, separators=(",", ":"))
    usati = sum(1 for t in tr if t["usato"])
    print(f"Rendimenti batteria: {len(tr)} tratti ({usati} da almeno {KWH_MIN_TRATTO} kWh); pesi carica "
          f"{ris['pesi']['carica']}, scarica {ris['pesi']['scarica']}; inverter {ris['inverter']['fonte']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:             # la simulazione non deve mai fermarsi per questo calcolo
        print(f"Rendimenti batteria: errore {ex}")
