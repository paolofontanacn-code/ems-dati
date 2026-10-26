# -*- coding: utf-8 -*-
# Revisione R06 - 26/10/2026 - a ogni decisione si salvano i piani completi calcolato e spedito (potenza in rete, energia
#   in batteria, carica/scarica, produzione prevista) con l'ora di fine dei calcoli (cessione/live/piani/, piano_ultimo.json);
#   prezzi noti fino all'ultimo disponibile (prezzi_noti.json); tolto il riassunto a testo del piano dal registro
# Revisione R05 - 26/10/2026 - regola di stabilita' (4 ore / +10 % / 0,10 EUR) prima di cambiare il piano spedito;
#   potenza TOU nel piano; carica 0-10 kW, scarica 2-10 kW
# Revisione R04 - 24/10/2026 - decisione con piano a fasce di 2 ore (modalita' diverse nello stesso giorno) cercato con algoritmo
#   evolutivo + semi lineari e fuzzy (cessione_ottimizza.py), modello fisico non lineare, prezzi mancanti previsti dallo
#   storico (orizzonte fino a fine domani), parametri tarati dall'apprendimento; contesto di ogni decisione salvato per il rigioco
# Revisione R03 - 23/10/2026 - prima versione: simulazione ogni 2 ore, da oggi in avanti
"""
cessione_live.py - SOLO SIMULAZIONE: impianto da 20 kW in cessione totale (vedi cessione_totale.py per l'impianto),
simulato DA OGGI IN AVANTI come se fosse governato davvero, con decisioni ogni 2 ore.

A ogni giro di GitHub (ogni 30 minuti):
 1. ESECUZIONE: i quarti d'ora per cui sono arrivate le letture di Cismondi (i dati piu' freschi) vengono "vissuti"
    dall'impianto simulato con la modalita' decisa in quel momento: produzione = Cismondi x 20/11 x rapporto Ovest/Sud.
    In parallelo: impianto senza batteria (scenario 0) e, per l'autoapprendimento, le altre modalita' (controfattuali).
 2. APPRENDIMENTO: per ogni modello meteo si misura l'errore della previsione di produzione (per orizzonte: entro 2 ore,
    2-12 ore, oltre) e la correzione per ora del giorno; per ogni modalita' lo scarto tra ricavo atteso e ricavo ottenuto.
 3. DECISIONE (a ogni nuova fascia di 2 ore: 00, 02, ... 22): si rivaluta tutto da capo:
    - previsione della produzione: irraggiamento orario da piu' modelli Open-Meteo (diretta e diffusa) -> piano Sud di
      Cismondi -> produzione di Cismondi (corretta con quanto imparato) -> piano Ovest dell'impianto; si usa, per ogni
      orizzonte, il modello con l'errore misurato piu' basso (media dei modelli finche' non ci sono abbastanza dati);
      correzione con le ultime letture reali (scarto che si attenua nelle ore successive);
    - prezzi orari NORD noti (oggi; domani dalle 13 circa);
    - prezzi: quelli noti e, oltre l'ultimo noto, la previsione dallo storico: orizzonte almeno fino a fine domani;
    - piano: per ogni fascia di 2 ore una modalita' Huawei (anche diverse nello stesso giorno) e per ogni ora il valore
      della fascia TOU o del comando, cercato con algoritmo evolutivo partendo da programmazione lineare, logica fuzzy,
      modalita' pure e piano precedente, valutato con il modello non lineare su 3 scenari di produzione
      (cessione_ottimizza.py); parametri tarati dall'apprendimento (cessione_apprendimento.py).
Uscite: cessione/live/ (stato.json, giornaliero.csv, giorni/AAAA-MM-GG.json, decisioni/AAAA-MM-GG.json,
        piani/AAAA-MM-GG.json, piano_ultimo.json, prezzi_noti.json)
"""
import csv
import datetime as dt
import glob
import json
import math
import os
import sys
import time
import urllib.parse

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cessione_totale as CT  # noqa: E402
import cessione_ottimizza as CO  # noqa: E402

OUT = os.path.join(CT.OUT, "live")
MODELLI = [m for m in os.environ.get("EMS_MODELLI_METEO_CESSIONE",
           "italia_meteo_arpae_icon_2i,meteofrance_seamless,icon_seamless,ecmwf_ifs025").split(",") if m]
MODI = CO.MODI
NOMI_MODI = CO.NOMI_MODI
TEMPO_DECISIONE_S = float(os.environ.get("EMS_TEMPO_DECISIONE", "90"))
PR_INIZIALE = 0.85              # resa iniziale: kW = 11 kW x irraggiamento / 1000 x 0,85 (poi corretta dai dati)
ALFA_ERRORE = 0.05              # peso di ogni nuovo quarto d'ora nell'errore medio dei modelli
ALFA_CORREZIONE = 0.05          # peso nella correzione per ora del giorno
MIN_CAMPIONI = 16               # quarti d'ora di giorno misurati prima di scegliere il modello migliore
MAX_FASCE_TOU = 14
TAU_ATTUALITA_S = 7200          # attenuazione della correzione con le ultime letture


def log(msg):
    print(f"Cessione ogni 2 ore: {msg}", flush=True)


def carica_json(f, predef):
    try:
        with open(f, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return predef


def salva_json(f, d, compatto=False):
    os.makedirs(os.path.dirname(f), exist_ok=True)
    tmp = f + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, separators=(",", ":") if compatto else None, indent=None if compatto else 1)
    os.replace(tmp, f)


def giorno_di(ts):
    return dt.datetime.fromtimestamp(ts, CT.ROMA).strftime("%Y-%m-%d")


def ora_di(ts):
    return dt.datetime.fromtimestamp(ts, CT.ROMA).hour


# ------------------------------------------------------------------ dati freschi di Cismondi
def letture_recenti(da_ts, adesso):
    """{ts: fv_w} di Cismondi da da_ts: giorni chiusi (dati/) + giorno in corso (memoria della simulazione o pannello)"""
    out = {}
    g0 = giorno_di(da_ts - 86400)
    for g, v in CT.letture_fv().items():
        if g >= g0:
            out.update({t: w for t, w in v.items() if da_ts - 3600 <= t <= adesso})
    files = sorted(glob.glob(os.path.join(CT.DATI, "dataset_????????.csv")))
    if not files and os.path.isfile(os.path.join(CT.RADICE, "pannello", "oggi.csv")):
        files = [os.path.join(CT.RADICE, "pannello", "oggi.csv")]
    for f in files[-2:]:
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                t, w = CT.numero(r.get("ts")), CT.numero(r.get("fv_w"))
                if t is not None and w is not None and da_ts - 3600 <= t <= adesso:
                    out[int(t)] = max(0.0, w)
    return out


def quarti_completi(letture, da_ts):
    """energia di Cismondi (kWh) per i quarti d'ora completi da da_ts in poi: {inizio_quarto: kWh}"""
    per = {}
    for t, w in letture.items():
        q = int(t // 900 * 900)
        if q >= da_ts:
            per.setdefault(q, []).append((t, w))
    out = {}
    ultimo = max(letture) if letture else 0
    for q in sorted(per):
        v = per[q]
        if len(v) >= 2 and (max(t for t, _ in v) >= q + 600 or ultimo >= q + 900):
            out[q] = sum(w for _, w in v) / len(v) / 1000 * CT.Q
        else:
            break                                   # i quarti si eseguono in ordine: ci si ferma al primo incompleto
    # nessun buco: si eseguono solo quarti consecutivi
    seq, atteso = {}, da_ts
    for q in sorted(out):
        if q != atteso:
            break
        seq[q] = out[q]
        atteso = q + 900
    return seq


# ------------------------------------------------------------------ R06: piani completi per la pagina
def curve_piano(contesto, piano):
    """curve attese di un piano sulla produzione prevista (scenario probabile): kW in rete, kWh in batteria, kW batteria"""
    quarti = contesto["quarti"]
    x = [piano.get(str(t), [0, 0.0]) for t in quarti]
    modi = np.array([[v[0] for v in x]])
    val = np.array([[v[1] for v in x]])
    cap = x[0][2] if len(x[0]) > 2 else CO.P_CMD_KW
    pv = np.asarray(contesto["p50"], dtype=float)[None, :]
    _, _, se = CO.simula(modi, val, pv, np.asarray(contesto["prezzi"], dtype=float), float(contesto["soc"]), dettaglio=True,
                         cap_kw=[cap])
    q = 1 / CT.Q
    return {"rete_kw": [round(v * q, 2) for v in se["ceduto"]], "soc_kwh": [round(v, 2) for v in se["soc"]],
            "batteria_kw": [round((c - d) * q, 2) for c, d in zip(se["carica"], se["scarica"])]}


def salva_piani(contesto, calcolato, spedito, t_fine, t_decisione, stab):
    voce = {"t_fine": int(t_fine), "t_decisione": int(t_decisione), "t_dati": int(contesto["t_dati"]),
            "inizio": int(contesto["quarti"][0]), "passo_s": 900, "cambiato": bool(stab.get("cambio")),
            "fv_prevista_kw": [round(v / CT.Q, 2) for v in contesto["p50"]],
            "prezzo": [round(v, 4) for v in contesto["prezzi"]], "prezzo_noto": contesto["noto"],
            "calcolato": curve_piano(contesto, calcolato), "spedito": curve_piano(contesto, spedito)}
    fp = os.path.join(OUT, "piani", giorno_di(t_fine) + ".json")
    reg = carica_json(fp, [])
    reg.append(voce)
    salva_json(fp, reg, compatto=True)
    salva_json(os.path.join(OUT, "piano_ultimo.json"), voce, compatto=True)


def salva_prezzi_noti(adesso):
    """prezzi NORD noti da ieri all'ultimo disponibile (una volta letti non cambiano)"""
    out = {}
    g = (dt.date.fromisoformat(giorno_di(adesso)) - dt.timedelta(days=1)).isoformat()
    for _ in range(4):
        t0, nq = CT.mezzanotte(g)
        pr, _ = CT.prezzi_giorno(g, nq, {"scaricati": CT.MAX_DOWNLOAD_GIRO})
        if pr is None:
            break
        out[g] = {"inizio": t0, "prezzi": [round(float(v), 5) for v in pr]}
        g = (dt.date.fromisoformat(g) + dt.timedelta(days=1)).isoformat()
    salva_json(os.path.join(OUT, "prezzi_noti.json"), {"aggiornato": dt.datetime.fromtimestamp(adesso, CT.ROMA).isoformat(timespec="minutes"),
                                                         "giorni": out}, compatto=True)
    return out


# ------------------------------------------------------------------ prezzi (solo file gia' scaricati: niente GME per il futuro)
def prezzi_quarti(t_da, t_a):
    """prezzi NORD orari ripetuti sui quarti d'ora tra t_da e t_a; si ferma al primo giorno senza prezzi"""
    out = {}
    g = giorno_di(t_da)
    while True:
        t0, nq = CT.mezzanotte(g)
        if t0 >= t_a:
            break
        pr, _ = CT.prezzi_giorno(g, nq, {"scaricati": CT.MAX_DOWNLOAD_GIRO})     # nessun nuovo download qui
        if pr is None:
            break
        for k in range(nq):
            t = t0 + k * 900
            if t_da <= t < t_a:
                out[t] = float(pr[k])
        g = (dt.date.fromisoformat(g) + dt.timedelta(days=1)).isoformat()
    return out


# ------------------------------------------------------------------ meteo e previsione della produzione
def meteo_modelli(luogo, cartella_giro):
    """radiazione oraria prevista da ogni modello: {modello: {ts_fine_ora: [ghi, dir, dif]}}; salvata per il giro"""
    out, errori = {}, {}
    for m in MODELLI:
        try:
            q = urllib.parse.urlencode({"latitude": luogo[0], "longitude": luogo[1], "models": m, "past_days": 1,
                                        "forecast_days": 3, "timeformat": "unixtime",
                                        "hourly": "shortwave_radiation,direct_radiation,diffuse_radiation"})
            r = CT.scarica_json(CT.URL_METEO + "?" + q, timeout=30)
            h = r.get("hourly") or {}
            serie = {}
            for i, t in enumerate(h.get("time") or []):
                def val(k):
                    for kk, v in h.items():
                        if (kk == k or kk.startswith(k + "_")) and isinstance(v, list) and i < len(v) and isinstance(v[i], (int, float)):
                            return float(v[i])
                    return None
                ghi, dr, df = val("shortwave_radiation"), val("direct_radiation"), val("diffuse_radiation")
                if ghi is None:
                    continue
                if dr is None or df is None:                 # modello senza diretta/diffusa: ripartizione fissa (segnalata)
                    dr, df = 0.7 * ghi, 0.3 * ghi
                serie[int(t)] = [ghi, dr, df]
            if len(serie) < 24:
                raise RuntimeError(f"solo {len(serie)} ore")
            out[m] = serie
        except Exception as e:
            errori[m] = str(e)[:160]
    if out:
        salva_json(os.path.join(cartella_giro), {m: {str(k): v for k, v in s.items()} for m, s in out.items()}, compatto=True)
    return out, errori


def previsione_modello(serie, quarti, luogo, corr_m):
    """per un modello: produzione prevista di Cismondi (Sud, kWh per quarto, gia' corretta) e rapporto Ovest/Sud"""
    q = np.asarray(quarti, dtype=float)
    fine_ora = (np.floor((q + 450 - 1) / 3600) + 1) * 3600
    v = np.array([serie.get(int(t), [np.nan] * 3) for t in fine_ora], dtype=float)
    ok = ~np.isnan(v[:, 0])
    v = np.nan_to_num(v)
    zen, az = CT.sole(fine_ora - 1800, *luogo)
    gs = CT.irraggiamento_piano(v[:, 0], v[:, 1], v[:, 2], zen, az, CT.INCLINAZIONE, CT.AZIMUT_CISMONDI)
    rapp = CT.rapporto_ovest(fine_ora, v[:, 0], v[:, 1], v[:, 2], *luogo)
    grezza = CT.P_CISMONDI_KW * gs / 1000 * PR_INIZIALE * CT.Q
    corr = np.array([corr_m.get(str(ora_di(t)), 1.0) for t in q])
    return np.where(ok, grezza, np.nan), np.where(ok, grezza * corr, np.nan), rapp


def fascia_orizzonte(sec):
    return "0-2h" if sec < 7200 else ("2-12h" if sec < 43200 else "oltre 12h")


# ------------------------------------------------------------------ principale
def main():
    os.makedirs(OUT, exist_ok=True)
    ora = dt.datetime.now(CT.ROMA)
    adesso = ora.timestamp() if not os.environ.get("EMS_ORA_REALE") else float(os.environ["EMS_ORA_REALE"])
    ora = dt.datetime.fromtimestamp(adesso, CT.ROMA)
    luogo = CT.coordinate()
    if not luogo:
        log("coordinate di Cismondi non disponibili (memoria della simulazione): rimando al prossimo giro")
        return
    fstato = os.path.join(OUT, "stato.json")
    st = carica_json(fstato, None)
    if not st:
        lett = letture_recenti(adesso - 6 * 3600, adesso)
        if not lett:
            log("nessuna lettura recente di Cismondi: rimando al prossimo giro")
            return
        ultimo = max(lett)
        partenza = int(ultimo // 900 * 900)            # da ora in avanti: si parte dal quarto d'ora in corso
        st = {"revisione": CT.REVISIONE, "inizio": partenza, "t_eseguito": partenza, "soc": 0.0,
              "corr": {m: {} for m in MODELLI}, "errore": {},
              "decisione": None, "giorni": {}}
        log(f"avvio della simulazione ogni 2 ore dal {dt.datetime.fromtimestamp(partenza, CT.ROMA):%d/%m/%Y %H:%M}")
    if st.get("decisione") and "piano" not in st["decisione"]:     # stato della R03: si decide subito con il nuovo metodo
        log("stato della revisione precedente: nuova decisione subito con il piano a fasce di 2 ore")
        st["decisione"], st["fascia_decisa"] = None, None
    st.pop("scarto_modi", None)
    st["revisione"] = CT.REVISIONE
    for m in MODELLI:
        st["corr"].setdefault(m, {})

    # ---------------- 1. esecuzione dei quarti d'ora arrivati
    lett = letture_recenti(st["t_eseguito"], adesso)
    nuovi = quarti_completi(lett, st["t_eseguito"])
    eseguiti = 0
    d = st.get("decisione")
    if d and nuovi:
        prezzi_n = prezzi_quarti(min(nuovi), max(nuovi) + 900)
        luogo_rad = {}
        for t, e_s in nuovi.items():
            if t not in prezzi_n:
                break
            # rapporto Ovest/Sud dalla radiazione del modello scelto (o media) per quell'ora
            rapp = d["rapporto"].get(str(t))
            if rapp is None:
                fo = (math.floor((t + 450 - 1) / 3600) + 1) * 3600
                if fo not in luogo_rad:
                    zen, _ = CT.sole([fo - 1800], *luogo)
                    cz = max(math.cos(math.radians(zen[0])), 0)
                    g = 1000 * cz ** 1.15
                    luogo_rad[fo] = float(CT.rapporto_ovest([fo], np.array([g]), np.array([0.8 * g]), np.array([0.2 * g]), *luogo)[0])
                rapp = luogo_rad[fo]
            pv = e_s * CT.SCALA * rapp
            pr = prezzi_n[t]
            gi = st["giorni"].setdefault(giorno_di(t), {"quarti": 0, "fv_kwh": 0.0, "p0_eur": 0.0, "batt_eur": 0.0, "carica_kwh": 0.0,
                                                        "scarica_kwh": 0.0, "tagliati_kwh": 0.0, "p0_ceduti_kwh": 0.0,
                                                        "batt_ceduti_kwh": 0.0, "modi": {m: 0 for m in MODI}, "decisioni": 0})
            c0, s0, ced0, _, _ = CT.passo("senza", pv, 0.0)
            voce = d["piano"].get(str(t), [0, 0.0])                     # oltre il piano: Fully fed to grid
            m_cod, val = voce[0], voce[1]
            cap = voce[2] if len(voce) > 2 else CO.P_CMD_KW
            modo = MODI[m_cod]
            c, s, ced, tagl, soc = CO.esegui_quarto(m_cod, val, pv, st["soc"], cap)
            st["soc"] = soc
            gi["quarti"] += 1
            gi["fv_kwh"] += pv
            gi["p0_eur"] += ced0 * pr
            gi["p0_ceduti_kwh"] += ced0
            gi["batt_eur"] += ced * pr
            gi["batt_ceduti_kwh"] += ced
            gi["carica_kwh"] += c
            gi["scarica_kwh"] += s
            gi["tagliati_kwh"] += tagl
            gi["modi"][modo] += 1
            gi["soc_fine"] = soc
            # apprendimento della previsione: errore per modello e orizzonte, correzione per ora del giorno
            h = str(ora_di(t))
            # errore per orizzonte: confronto con le previsioni di tutte le decisioni delle ultime 24 ore
            for arch in st.get("prev_archivio", []):
                orizz = fascia_orizzonte(t - arch["t_dati"])
                for m, prev in arch["prev"].items():
                    g_raw = prev.get(str(t))
                    if g_raw is None or (g_raw <= 0.002 and e_s <= 0.002):
                        continue
                    er = st["errore"].setdefault(m, {}).setdefault(orizz, {"mae": None, "n": 0})
                    a = abs(g_raw * st["corr"][m].get(h, 1.0) - e_s)
                    er["mae"] = a if er["mae"] is None else er["mae"] + ALFA_ERRORE * (a - er["mae"])
                    er["n"] += 1
            # correzione per ora del giorno: solo con la previsione della decisione in corso (una volta per quarto)
            for m, prev in d["prev_grezza"].items():
                g_raw = prev.get(str(t))
                if g_raw is None:
                    continue
                corr = st["corr"][m].get(h, 1.0)
                if g_raw > 0.05:                         # oltre 200 W: si aggiorna la correzione dell'ora
                    nuova = corr + ALFA_CORREZIONE * (min(2.5, e_s / g_raw) - corr)
                    st["corr"][m][h] = round(min(2.0, max(0.3, nuova)), 4)
            # registro del quarto d'ora per la pagina
            fq = os.path.join(OUT, "giorni", giorno_di(t) + ".json")
            reg = carica_json(fq, {"giorno": giorno_di(t), "quarti": []})
            reg["quarti"].append({"t": t, "fv": round(pv, 4), "prev": d["prev_ovest"].get(str(t)), "prezzo": round(pr, 5), "modo": modo,
                                  "valore": round(val, 3),
                                  "carica": round(c, 4), "scarica": round(s, 4), "ceduto": round(ced, 4), "ceduto0": round(ced0, 4),
                                  "tagliato": round(tagl, 4), "soc": round(soc, 3)})
            salva_json(fq, reg, compatto=True)
            st["t_eseguito"] = t + 900
            eseguiti += 1

    # ---------------- 2. nuova decisione a ogni fascia di 2 ore
    fascia = ora.strftime("%Y-%m-%d ") + f"{ora.hour // 2 * 2:02d}"
    if st.get("fascia_decisa") != fascia:
        t_inizio_calcoli = time.perf_counter()
        t_dati = st["t_eseguito"]
        cart_giro = os.path.join(OUT, "meteo", ora.strftime("%Y%m%d_%H%M") + ".json")
        meteo, errori_meteo = meteo_modelli(luogo, cart_giro)
        # orizzonte: fino a fine domani (prezzi noti dove ci sono, altrimenti previsti dallo storico)
        g_fine = (dt.date.fromisoformat(giorno_di(t_dati)) + dt.timedelta(days=2)).isoformat()
        t_fine = CT.mezzanotte(g_fine)[0]
        noti = prezzi_quarti(t_dati, t_fine)
        quarti = list(range(int(t_dati), int(t_fine), 900))
        if not meteo or len(quarti) < 4:
            log(f"decisione rimandata: meteo {'ok' if meteo else 'non disponibile ' + str(errori_meteo)}, quarti con prezzo {len(quarti)}")
        else:
            prev_s, prev_grezza, rapp_m = {}, {}, {}
            for m, serie in meteo.items():
                grezza, corretta, rapp = previsione_modello(serie, quarti, luogo, st["corr"].get(m, {}))
                prev_grezza[m], prev_s[m], rapp_m[m] = grezza, corretta, rapp
            # modello migliore per orizzonte (errore misurato), altrimenti media dei modelli
            scelta, sud = {}, np.zeros(len(quarti))
            for k, t in enumerate(quarti):
                o = fascia_orizzonte(t - t_dati)
                cand = [(st["errore"].get(m, {}).get(o, {}).get("mae"), m) for m in prev_s
                        if st["errore"].get(m, {}).get(o, {}).get("n", 0) >= MIN_CAMPIONI and not np.isnan(prev_s[m][k])]
                if cand:
                    m = min(cand)[1]
                    scelta[o] = m
                    sud[k] = prev_s[m][k]
                else:
                    v = [prev_s[m][k] for m in prev_s if not np.isnan(prev_s[m][k])]
                    sud[k] = float(np.mean(v)) if v else 0.0
                    scelta.setdefault(o, "media dei modelli")
            rapp = np.nanmean(np.vstack([rapp_m[m] for m in rapp_m]), axis=0)
            # correzione con le ultime letture reali (ultima ora eseguita)
            ultimi = [t for t in sorted(nuovi)][-4:] if nuovi else []
            fattore_att = 1.0
            if ultimi and d:
                reale = sum(nuovi[t] for t in ultimi)
                prevista = sum(sum(v.get(str(t), 0.0) for v in [d["prev_sud"]]) for t in ultimi)
                if prevista > 0.2:
                    fattore_att = min(1.7, max(0.3, reale / prevista))
            att = np.array([1 + (fattore_att - 1) * math.exp(-max(0, t - t_dati) / TAU_ATTUALITA_S) for t in quarti])
            sud = sud * att
            ovest = sud * CT.SCALA * rapp
            # incertezza: dispersione tra i modelli + errore medio misurato dell'orizzonte (piano Ovest)
            with np.errstate(all="ignore"):
                disp = np.nanstd(np.vstack([prev_s[m] for m in prev_s]), axis=0) if len(prev_s) > 1 else np.zeros(len(quarti))
            def mae_medio(t):
                v = [st["errore"].get(m, {}).get(fascia_orizzonte(t - t_dati), {}).get("mae") for m in prev_s]
                v = [x for x in v if x is not None]
                return float(np.mean(v)) if v else np.nan
            mae = np.array([mae_medio(t) for t in quarti])
            mae = np.where(np.isnan(mae), 0.15 * sud, mae)                       # senza misure: 15 % della previsione
            sigma = np.sqrt(np.nan_to_num(disp) ** 2 + np.where(sud > 0.002, mae, 0) ** 2) * CT.SCALA * rapp
            pr, noto = CO.prezzi_orizzonte(quarti, noti)
            theta = CO.carica_theta()
            contesto = {"t_dati": int(t_dati), "soc": round(st["soc"], 4), "quarti": quarti,
                        "p50": [round(float(v), 5) for v in ovest], "sigma": [round(float(v), 5) for v in sigma],
                        "prezzi": [round(float(v), 6) for v in pr], "noto": [bool(v) for v in noto]}
            salva_json(os.path.join(OUT, "contesti", f"{int(t_dati)}.json"), contesto, compatto=True)
            ris = CO.decidi(contesto, theta, tempo_s=TEMPO_DECISIONE_S, seme=int(t_dati) % 100000,
                            precedente=(d or {}).get("piano"))
            piano, stab = CO.stabilita(contesto, theta, ris["piano"], (d or {}).get("piano"))
            modo = MODI[piano[str(quarti[0])][0]]
            d = {"t_decisione": int(adesso), "fascia": fascia, "t_dati": t_dati, "modo": modo, "soc": round(st["soc"], 3),
                 "piano": piano, "atteso_eur": ris["atteso_eur"],
                 "prev_grezza": {m: {str(t): round(float(v), 5) for t, v in zip(quarti, prev_grezza[m][:]) if not np.isnan(v)}
                                 for m in prev_grezza},
                 "prev_sud": {str(t): round(float(v), 5) for t, v in zip(quarti, sud)},
                 "prev_ovest": {str(t): round(float(v), 5) for t, v in zip(quarti, ovest)},
                 "rapporto": {str(t): round(float(v), 4) for t, v in zip(quarti, rapp)}}
            st["decisione"] = d
            t_fine_calcoli = adesso + (time.perf_counter() - t_inizio_calcoli)      # ora di fine = ora di "invio" del piano
            d["t_fine"] = int(t_fine_calcoli)
            salva_piani(contesto, ris["piano"], piano, t_fine_calcoli, adesso, stab)
            st["fascia_decisa"] = fascia
            arch = [x for x in st.get("prev_archivio", []) if x["t_dati"] > t_dati - 86400]
            arch.append({"t_dati": t_dati, "prev": d["prev_grezza"]})
            st["prev_archivio"] = arch[-13:]
            gi = st["giorni"].setdefault(giorno_di(t_dati), {"quarti": 0, "fv_kwh": 0.0, "p0_eur": 0.0, "batt_eur": 0.0,
                                                             "carica_kwh": 0.0, "scarica_kwh": 0.0, "tagliati_kwh": 0.0,
                                                             "p0_ceduti_kwh": 0.0, "batt_ceduti_kwh": 0.0,
                                                             "modi": {m: 0 for m in MODI}, "decisioni": 0})
            gi["decisioni"] += 1
            fd = os.path.join(OUT, "decisioni", ora.strftime("%Y-%m-%d") + ".json")
            reg = carica_json(fd, [])
            reg.append({"ora": ora.isoformat(timespec="minutes"), "dati_fino_a": dt.datetime.fromtimestamp(t_dati, CT.ROMA).isoformat(timespec="minutes"),
                        "soc_kwh": round(st["soc"], 2), "modo": modo, "nome_modo": NOMI_MODI[modo],
                        "atteso_eur": ris["atteso_eur"], "punteggi_semi": ris["punteggi_semi"],
                        "fine_calcoli": dt.datetime.fromtimestamp(t_fine_calcoli, CT.ROMA).isoformat(timespec="seconds"), "stabilita": stab,
                        "generazioni": ris["generazioni"], "valutazioni": ris["valutazioni"], "secondi": ris["secondi"],
                        "ore_prezzo_previsto": int((~noto).sum() // 4), "theta": theta,
                        "orizzonte_fino_a": dt.datetime.fromtimestamp(quarti[-1] + 900, CT.ROMA).isoformat(timespec="minutes"),
                        "previsione_kwh": round(float(ovest.sum()), 2), "modelli": sorted(meteo), "modelli_errore": errori_meteo,
                        "modello_per_orizzonte": scelta, "correzione_ultime_letture": round(fattore_att, 3)})
            salva_json(fd, reg)
            log(f"decisione {fascia}: {'piano CAMBIATO' if stab['cambio'] else 'piano spedito MANTENUTO'} ({stab['motivo']}); ora {NOMI_MODI[modo]}, ricavo atteso {ris['atteso_eur']:.2f} EUR fino a fine domani "
                f"({ris['generazioni']} generazioni, {ris['valutazioni']} piani provati in {ris['secondi']} s; ore con prezzo previsto "
                f"{int((~noto).sum() // 4)}); modelli meteo {len(meteo)}")
    # ---------------- 3. uscite
    try:
        salva_prezzi_noti(adesso)
    except Exception as ex:                      # la pagina ne fa a meno
        log(f"prezzi noti non salvati: {ex}")
    salva_json(fstato, st, compatto=True)
    col = ["giorno", "quarti", "decisioni", "fv_kwh", "p0_ceduti_kwh", "p0_eur", "batt_ceduti_kwh", "batt_eur", "beneficio_eur",
           "carica_kwh", "scarica_kwh", "tagliati_kwh", "soc_fine", "quarti_fully", "quarti_tou", "quarti_terzi"]
    with open(os.path.join(OUT, "giornaliero.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=col)
        w.writeheader()
        for g in sorted(st["giorni"]):
            x = st["giorni"][g]
            w.writerow({"giorno": g, "quarti": x["quarti"], "decisioni": x["decisioni"], "fv_kwh": round(x["fv_kwh"], 3),
                        "p0_ceduti_kwh": round(x["p0_ceduti_kwh"], 3), "p0_eur": round(x["p0_eur"], 4),
                        "batt_ceduti_kwh": round(x["batt_ceduti_kwh"], 3), "batt_eur": round(x["batt_eur"], 4),
                        "beneficio_eur": round(x["batt_eur"] - x["p0_eur"], 4), "carica_kwh": round(x["carica_kwh"], 3),
                        "scarica_kwh": round(x["scarica_kwh"], 3), "tagliati_kwh": round(x["tagliati_kwh"], 3),
                        "soc_fine": round(x.get("soc_fine", 0.0), 3), "quarti_fully": x["modi"]["fully"],
                        "quarti_tou": x["modi"]["tou"], "quarti_terzi": x["modi"]["terzi"]})
    salva_json(os.path.join(OUT, "indice.json"), {
        "aggiornato": dt.datetime.now(CT.ROMA).isoformat(timespec="seconds"), "revisione": CT.REVISIONE,
        "inizio": dt.datetime.fromtimestamp(st["inizio"], CT.ROMA).isoformat(timespec="minutes"),
        "eseguito_fino_a": dt.datetime.fromtimestamp(st["t_eseguito"], CT.ROMA).isoformat(timespec="minutes"),
        "soc_kwh": round(st["soc"], 3), "modo_attuale": (st.get("decisione") or {}).get("modo"),
        "errore_modelli": st["errore"], "modelli": MODELLI, "theta": CO.carica_theta()})
    log(f"quarti d'ora eseguiti in questo giro: {eseguiti}; eseguito fino a "
        f"{dt.datetime.fromtimestamp(st['t_eseguito'], CT.ROMA):%d/%m %H:%M}; batteria {st['soc']:.1f} kWh")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:          # la simulazione principale non deve mai fermarsi per questa pagina
        import traceback
        traceback.print_exc()
        print(f"Cessione ogni 2 ore: errore {ex}")
        sys.exit(0)
