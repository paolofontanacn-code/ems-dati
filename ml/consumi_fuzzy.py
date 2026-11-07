# -*- coding: utf-8 -*-
# Revisione R08 - 07/11/2026 - (tesi Dabbicco, PoliTo 2022) consumi delle stesse ore del giorno prima e della settimana
#   prima come ingressi, scelti dall'automiglioramento solo se fanno sbagliare meno; frequenza dei carichi ripetitivi
# Revisione R07 - 31/10/2026 - prima versione: stima dei consumi della casa con logica fuzzy autoapprendente
"""
consumi_fuzzy.py - SOLO SIMULAZIONE: stima dei consumi della casa di Cismondi con LOGICA FUZZY (modello di Takagi-Sugeno
di ordine 0: ogni regola "SE ... ALLORA consumo = c" ha un valore c imparato dai dati reali).

Ingressi (per quarto d'ora):
  - ora del giorno (insiemi fuzzy triangolari, uno per ora; 6 fasce di 4 ore per il riscaldamento);
  - tipo di giorno (lavoro, sabato, festa);
  - TEMPERATURA EFFICACE della casa = temperatura esterna filtrata con l'INERZIA della casa (media esponenziale con
    costante di tempo "inerzia_ore"): insiemi molto freddo ... caldo;
  - temperatura esterna del momento (resa della pompa di calore per l'acqua calda);
  - sole (radiazione: apporti gratuiti che riducono il riscaldamento);
  - consumi PREGRESSI: consumo medio del giorno prima rispetto al consumo tipico (basso, normale, alto);
  - (R08) consumo medio della STESSA ORA del giorno prima e dello stesso giorno della SETTIMANA PRIMA (insiemi
    basso ... molto alto): dalla tesi "Analisi dei metodi di ricostruzione delle curve di carico" (la ripetitivita'
    settimanale e' piu' forte di quella giornaliera). Si usano solo se, nella prova degli ultimi giorni, fanno sbagliare
    meno (l'automiglioramento prova il modello con e senza).
Regole (il consumo totale e' la somma delle parti, la pompa di calore non e' misurata a parte):
  - comportamento:      SE ora = h E giorno = g                        ALLORA c
  - riscaldamento PdC:  SE fascia = f E temperatura efficace = T        ALLORA c >= 0   (ripetuto ogni giorno)
                        SE fascia = f E sole E fa freddo               ALLORA c <= 0   (apporti solari)
  - acqua calda (ACS):  SE ora = h E temperatura esterna = T           ALLORA c >= 0   (uguale per tutti i giorni:
                        e' la parte che si ripete ogni giorno alla stessa ora, piu' alta col freddo)
  - pregresso:          SE consumo del giorno prima = basso/normale/alto ALLORA c
AUTOAPPRENDIMENTO: i valori delle regole si ricalcolano a ogni giro con tutti i dati reali (minimi quadrati con limiti
di segno, i giorni recenti pesano di piu': fattore di oblio).
AUTOMIGLIORAMENTO: a ogni giro si provano piu' combinazioni di inerzia della casa e oblio; si tiene quella che sbaglia
meno sugli ultimi giorni (prova fuori campione: addestramento sui giorni prima). Lo storico delle prove e' salvato.
La separazione tra comportamento, riscaldamento e acqua calda e' una STIMA (c'e' solo il consumo totale).
"""
import itertools

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

GRUPPI = ["lavoro", "sabato", "festa"]
GRUPPO = {"feriale": "lavoro", "ponte": "lavoro", "sabato": "sabato", "domenica": "festa", "festivo": "festa"}
CENTRI_T_EFF = [-5.0, 0.0, 5.0, 10.0, 15.0, 20.0]       # molto freddo, freddo, fresco, mite, tiepido, caldo
CENTRI_T_ACS = [0.0, 10.0, 20.0]
CENTRI_PREG = [0.7, 1.0, 1.3]                            # consumo del giorno prima / consumo tipico
FASCE = 6                                                # fasce di 4 ore per il riscaldamento
INERZIE_ORE = [3, 6, 12, 24, 48]                         # candidati per l'automiglioramento
OBLII = [0.98, 0.995]                                    # peso di un giorno piu' vecchio di un giorno
RITARDI = [False, True]                                  # R08: con o senza i consumi delle stesse ore di giorni prima
CENTRI_ORA_PREC = [300.0, 800.0, 1500.0, 2500.0]         # W medi dell'ora: basso, medio, alto, molto alto
SOGLIA_PICCO_W = 2000.0                                  # R08: carichi ripetitivi (frequenza per ora)
RIDGE = 3.0                                              # regolarizzazione (rende unica la separazione delle parti)
P_MAX_W = 12000.0


# ------------------------------------------------------------------ insiemi fuzzy
def triangolari(x, centri):
    """gradi di appartenenza (N, len(centri)) a insiemi triangolari con spalle agli estremi (somma = 1)"""
    x = np.asarray(x, dtype=float)
    c = np.asarray(centri, dtype=float)
    x = np.clip(x, c[0], c[-1])
    mu = np.zeros((len(x), len(c)))
    for i in range(len(c)):
        if i > 0:
            s = (x >= c[i - 1]) & (x <= c[i])
            mu[s, i] = (x[s] - c[i - 1]) / (c[i] - c[i - 1])
        if i < len(c) - 1:
            s = (x >= c[i]) & (x <= c[i + 1])
            mu[s, i] = np.maximum(mu[s, i], (c[i + 1] - x[s]) / (c[i + 1] - c[i]))
    return mu


def circolari(ora, n):
    """n insiemi triangolari sull'ora del giorno (0-24, circolare): somma = 1"""
    passo = 24.0 / n
    pos = (np.asarray(ora, dtype=float) % 24.0) / passo
    i0 = np.floor(pos).astype(int) % n
    f = pos - np.floor(pos)
    mu = np.zeros((len(pos), n))
    mu[np.arange(len(pos)), i0] = 1 - f
    mu[np.arange(len(pos)), (i0 + 1) % n] += f
    return mu


def temperatura_efficace(ts, temp, inerzia_ore):
    """temperatura esterna filtrata con l'inerzia della casa (media esponenziale; si riparte dopo 6 ore senza dati)"""
    out = np.full(len(ts), np.nan)
    tau = inerzia_ore * 3600.0
    v, t_prec = None, None
    for i, (t, x) in enumerate(zip(ts, temp)):
        if x is None or np.isnan(x):
            out[i] = v if v is not None else np.nan
            continue
        if v is None or t_prec is None or t - t_prec > 6 * 3600:
            v = x
        else:
            a = 1 - np.exp(-(t - t_prec) / tau)
            v = v + a * (x - v)
        t_prec = t
        out[i] = v
    return out


# ------------------------------------------------------------------ matrice delle regole
def matrice(ora, gruppo, t_eff, t_ext, ghi, rapporto_preg, ora_prec=None):
    """gradi di attivazione delle regole (N, K) e limiti dei valori delle regole"""
    n = len(ora)
    mu_h = circolari(ora, 24)
    mu_f = circolari(ora, FASCE)
    g = np.zeros((n, len(GRUPPI)))
    for i, x in enumerate(gruppo):
        g[i, GRUPPI.index(x)] = 1
    mu_te = triangolari(np.nan_to_num(t_eff, nan=12.0), CENTRI_T_EFF)
    mu_ta = triangolari(np.nan_to_num(t_ext, nan=12.0), CENTRI_T_ACS)
    mu_p = triangolari(np.nan_to_num(rapporto_preg, nan=1.0), CENTRI_PREG)
    freddo = 1 - triangolari(np.nan_to_num(t_eff, nan=12.0), [10.0, 18.0])[:, 1]       # 1 sotto 10 gradi, 0 sopra 18
    sole = np.nan_to_num(ghi, nan=0.0) / 1000.0
    blocchi, basso, alto, nomi = [], [], [], []
    comp = (mu_h[:, :, None] * g[:, None, :]).reshape(n, -1)                            # comportamento
    blocchi.append(comp); basso += [0] * comp.shape[1]; alto += [P_MAX_W] * comp.shape[1]
    nomi += [f"comportamento|{h}|{gg}" for h in range(24) for gg in GRUPPI]
    risc = (mu_f[:, :, None] * mu_te[:, None, :]).reshape(n, -1)                        # riscaldamento
    blocchi.append(risc); basso += [0] * risc.shape[1]; alto += [P_MAX_W] * risc.shape[1]
    nomi += [f"riscaldamento|{f}|{t}" for f in range(FASCE) for t in CENTRI_T_EFF]
    sol = mu_f * (sole * freddo)[:, None]                                               # apporti solari
    blocchi.append(sol); basso += [-P_MAX_W] * FASCE; alto += [0] * FASCE
    nomi += [f"sole|{f}" for f in range(FASCE)]
    acs = (mu_h[:, :, None] * mu_ta[:, None, :]).reshape(n, -1)                         # acqua calda
    blocchi.append(acs); basso += [0] * acs.shape[1]; alto += [P_MAX_W] * acs.shape[1]
    nomi += [f"acs|{h}|{t}" for h in range(24) for t in CENTRI_T_ACS]
    blocchi.append(mu_p); basso += [-P_MAX_W] * 3; alto += [P_MAX_W] * 3                # pregresso
    nomi += [f"pregresso|{p}" for p in CENTRI_PREG]
    if ora_prec is not None:                                                            # R08: stesse ore, giorni prima
        for nome, v in (("giorno_prima", ora_prec[0]), ("settimana_prima", ora_prec[1])):
            mu = triangolari(v, CENTRI_ORA_PREC)
            blocchi.append(mu); basso += [-P_MAX_W] * mu.shape[1]; alto += [P_MAX_W] * mu.shape[1]
            nomi += [f"{nome}|{x}" for x in CENTRI_ORA_PREC]
    return np.hstack(blocchi), np.array(basso, float), np.array(alto, float), nomi


def pregresso(ts, carico, data):
    """consumo medio del giorno prima di ogni quarto d'ora (W); nan se il giorno prima ha meno di 48 quarti d'ora"""
    medie = {}
    for d in np.unique(data):
        m = data == d
        v = carico[m]
        v = v[~np.isnan(v)]
        if len(v) >= 48:
            medie[d] = float(np.mean(v))
    out = np.full(len(ts), np.nan)
    import datetime as _dt
    for i, d in enumerate(data):
        out[i] = medie.get(d - _dt.timedelta(days=1), np.nan)
    return out, medie


def ore_prima(df, tipico):
    """R08: consumo medio della stessa ora del giorno prima e dello stesso giorno della settimana prima (W);
    se uno manca si usa l'altro, se mancano entrambi il consumo tipico"""
    import datetime as _dt
    ora = ((df["qo"].to_numpy() - 1) // 4).astype(int)
    medie = df.assign(_o=ora).groupby(["data", "_o"])["carico_w"].mean().to_dict()
    g1 = np.array([medie.get((d - _dt.timedelta(days=1), o), np.nan) for d, o in zip(df["data"], ora)], dtype=float)
    g7 = np.array([medie.get((d - _dt.timedelta(days=7), o), np.nan) for d, o in zip(df["data"], ora)], dtype=float)
    g1 = np.where(np.isnan(g1), g7, g1)
    g7 = np.where(np.isnan(g7), g1, g7)
    return np.nan_to_num(g1, nan=tipico), np.nan_to_num(g7, nan=tipico)


def ingressi(df, inerzia_ore, tipico, ritardi=False):
    t_eff = temperatura_efficace(df["ts"].to_numpy(), df["temp"].to_numpy(dtype=float), inerzia_ore)
    preg, _ = pregresso(df["ts"].to_numpy(), df["carico_w"].to_numpy(dtype=float), df["data"].to_numpy())
    ora = (df["qo"].to_numpy() - 1) / 4.0 + 0.125
    gr = [GRUPPO[t] for t in df["tipo"]]
    op = ore_prima(df, tipico) if ritardi else None
    return ora, gr, t_eff, df["temp"].to_numpy(dtype=float), df["ghi"].to_numpy(dtype=float), preg / tipico, op


# ------------------------------------------------------------------ addestramento e stima
def addestra(df, inerzia_ore, oblio, ritardi=False):
    if len(df[df["carico_w"].notna()]) < 96 * 5:
        return None
    tipico = float(df["carico_w"].mean())
    ora, gr, te, ta, ghi, rp, op = ingressi(df, inerzia_ore, tipico, ritardi)
    m = df["carico_w"].notna().to_numpy()
    d = df[m]
    ora, te, ta, ghi, rp = ora[m], te[m], ta[m], ghi[m], rp[m]
    gr = [x for x, k in zip(gr, m) if k]
    op = None if op is None else (op[0][m], op[1][m])
    X, lo, hi, nomi = matrice(ora, gr, te, ta, ghi, rp, op)
    y = d["carico_w"].to_numpy(dtype=float)
    giorni = (d["ts"].max() - d["ts"].to_numpy()) / 86400.0
    w = np.sqrt(oblio ** giorni)
    A = np.vstack([X * w[:, None], np.sqrt(RIDGE) * np.eye(X.shape[1])])
    b = np.concatenate([y * w, np.zeros(X.shape[1])])
    ris = lsq_linear(A, b, bounds=(lo, hi), lsmr_tol="auto", max_iter=2000)
    return {"inerzia_ore": inerzia_ore, "oblio": oblio, "ritardi": bool(ritardi), "tipico_w": tipico, "valori": ris.x, "nomi": nomi}


def stima(mod, df_storia, df_target):
    """stima (W) per i quarti di df_target; df_storia = dati reali prima (temperature per l'inerzia, consumi pregressi)"""
    import pandas as pd
    tutto = pd.concat([df_storia.tail(96 * 9), df_target], ignore_index=True).sort_values("ts").drop_duplicates("ts", keep="last")
    ora, gr, te, ta, ghi, rp, op = ingressi(tutto, mod["inerzia_ore"], mod["tipico_w"], mod.get("ritardi", False))
    # consumo pregresso del giorno target: se il giorno prima non e' completo si usano le ultime 24 ore disponibili
    if np.isnan(rp).any():
        v = df_storia["carico_w"].dropna().tail(96).to_numpy(dtype=float)
        if len(v) >= 48:
            rp = np.where(np.isnan(rp), float(v.mean()) / mod["tipico_w"], rp)
    X, *_ = matrice(ora, gr, te, ta, ghi, rp, op)
    p = np.clip(X @ mod["valori"], 0, P_MAX_W)
    m = tutto["ts"].isin(df_target["ts"]).to_numpy()
    return dict(zip(tutto["ts"].to_numpy()[m].tolist(), p[m].tolist()))


def mae(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = ~(np.isnan(a) | np.isnan(b))
    return float(np.mean(np.abs(a[m] - b[m]))) if m.any() else None


def scegli(train, test, test_prev=None):
    """automiglioramento: prova le combinazioni di inerzia, oblio e (R08) consumi delle ore dei giorni prima.
    test_prev = gli stessi quarti con il meteo PREVISTO (R08: verifica come le previsioni del Mango); se manca si usa
    test. I consumi dei giorni di prova si stimano con i soli dati prima di ogni giorno (niente consumi del giorno stesso).
    Ritorna (migliore = (errore, inerzia, oblio, ritardi), elenco delle prove)"""
    prove, migliore = [], None
    tp = test if test_prev is None else test_prev
    for inerzia, oblio, rit in itertools.product(INERZIE_ORE, OBLII, RITARDI):
        mod = addestra(train, inerzia, oblio, rit)
        if mod is None:
            continue
        p = {}
        storia = train
        for d in sorted(tp["data"].unique()):
            x = tp[tp["data"] == d].copy()
            x["carico_w"] = np.nan
            p.update(stima(mod, storia, x))
            storia = pd.concat([storia, test[test["data"] == d]], ignore_index=True)
        e = mae([p.get(t, np.nan) for t in test["ts"]], test["carico_w"].to_numpy(dtype=float))
        prove.append({"inerzia_ore": inerzia, "oblio": oblio, "ritardi": rit, "mae_w": None if e is None else round(e, 1)})
        if e is not None and (migliore is None or e < migliore[0]):
            migliore = (e, inerzia, oblio, rit)
    return migliore, prove


def incidenze(mod):
    """lettura delle regole imparate: riscaldamento per temperatura efficace, acqua calda per ora, pregresso"""
    v = dict(zip(mod["nomi"], mod["valori"]))
    risc = {str(t): round(float(np.mean([v[f"riscaldamento|{f}|{t}"] for f in range(FASCE)])), 1) for t in CENTRI_T_EFF}
    acs = {str(t): round(float(sum(v[f"acs|{h}|{t}"] for h in range(24)) / 1000.0), 2) for t in CENTRI_T_ACS}
    preg = {str(p): round(float(v[f"pregresso|{p}"]), 1) for p in CENTRI_PREG}
    comp = {g: round(float(sum(v[f"comportamento|{h}|{g}"] for h in range(24)) / 1000.0), 2) for g in GRUPPI}
    rit = {}
    for nome in ("giorno_prima", "settimana_prima"):
        if f"{nome}|{CENTRI_ORA_PREC[0]}" in v:
            rit[nome] = {str(x): round(float(v[f"{nome}|{x}"]), 1) for x in CENTRI_ORA_PREC}
    return {"riscaldamento_w_per_temperatura_efficace": risc, "ore_dei_giorni_prima_w": rit or None, "acqua_calda_kwh_giorno_per_temperatura": acs,
            "pregresso_w_per_rapporto_giorno_prima": preg, "comportamento_kwh_giorno": comp,
            "nota": "valori medi delle regole; la separazione tra le parti e' una stima (c'e' solo il consumo totale)"}


def carichi_ripetitivi(df, giorni=30):
    """R08 (tesi, cap. 5): per ogni ora, quota dei giorni (ultimi 'giorni') con almeno un quarto d'ora sopra
    SOGLIA_PICCO_W. Un carico si potrebbe inserire nella stima come andamento tipo solo se quasi certo (tesi: 25 giorni
    su 30); qui si misura e basta: la stima resta livellata (decisione dell'utente del 07/11/2026)."""
    d = df[df["data"] >= sorted(df["data"].unique())[-giorni]] if len(df) else df
    if d.empty:
        return None
    ora = (d["qo"] - 1) // 4
    q = (d["carico_w"] > SOGLIA_PICCO_W).groupby([d["data"], ora]).any().unstack(fill_value=False)
    quota = q.mean()
    return {"soglia_w": SOGLIA_PICCO_W, "giorni": int(q.shape[0]),
            "quota_giorni_per_ora": {str(int(h)): round(float(v), 2) for h, v in quota.items()},
            "quasi_certi_ore": [int(h) for h, v in quota.items() if v >= 25 / 30]}
