# -*- coding: utf-8 -*-
# Revisione R05 - 26/10/2026 - scarica modulabile 2-10 kW (2 batterie da 2-5 kW: sotto 2 kW ferma), carica 0-10 kW;
#   potenza massima di scarica in TOU scelta dal piano (2-10 kW, impostabile via API 5.2.5); a parita' di ricavo meno
#   cambi di comando; regola di stabilita' 4 ore / +10 % / 0,10 EUR prima di cambiare il piano spedito
# Revisione R04 - 24/10/2026 - prima versione: modello fisico non lineare, previsione dei prezzi mancanti, scenari di
#   produzione, piano con modalita' diverse nello stesso giorno (fasce di 2 ore) cercato con algoritmo evolutivo,
#   semi da programmazione lineare e da logica fuzzy; usato dalla decisione ogni 2 ore e dall'apprendimento
"""
cessione_ottimizza.py - SOLO SIMULAZIONE: cervello delle decisioni della cessione totale (impianto in cessione_totale.py).

PIANO = per ogni fascia di 2 ore (00-02, 02-04, ...) una modalita' Huawei, e per ogni ora un valore v tra -1 e +1:
  Fully fed to grid : v non usato (la batteria prende solo la produzione oltre il limite e scarica fino al limite)
  TOU               : v > +1/3 = fascia di CARICA (i pannelli caricano prima la batteria), v < -1/3 = fascia di SCARICA
                      (la batteria cede in rete, i pannelli hanno la precedenza sul limite), altrimenti nessuna fascia;
                      al massimo 14 fasce al giorno
  Third-party       : comando di potenza v x 10 kW (+ carica dai pannelli, - scarica in rete; in scarica la produzione
                      oltre il limite si perde)
MODELLO FISICO (non lineare, ipotesi dichiarate): perdita totale 5 % tra carica e scarica alla potenza piena, piu' una
  perdita che cresce alle basse potenze di scarica (fino a +4 %); potenza di carica ridotta nell'ultimo 5 % della batteria,
  potenza di scarica ridotta nel primo 5 %.
VALUTAZIONE di un piano: ricavo su 3 scenari di produzione (bassa, probabile, alta) pesati, piu' il valore dell'energia
  che resta in batteria a fine orizzonte, meno penalita' (cambi di modalita', fasce TOU oltre 14).
RICERCA: algoritmo evolutivo (popolazione, incrocio, mutazione, elitismo) partendo da semi: programmazione lineare,
  logica fuzzy (prezzo basso + sole -> carica; prezzo alto -> scarica), modalita' pure, piano precedente.
PARAMETRI (theta) tarati dall'apprendimento (cessione_apprendimento.py) rigiocando i giorni vissuti.
"""
import datetime as dt
import glob
import json
import math
import os
import time

import numpy as np

import cessione_totale as CT

MODI = ("fully", "tou", "terzi")
NOMI_MODI = {"fully": "Fully fed to grid", "tou": "TOU", "terzi": "Third-party dispatch"}
ETA_C = math.sqrt(1 - CT.PERDITA_CICLO)        # rendimento di carica
ETA_D = math.sqrt(1 - CT.PERDITA_CICLO)        # rendimento di scarica alla potenza piena
PERDITA_BASSA_POT = 0.04                       # perdita in piu' a bassa potenza di scarica
POT_RIF_KW = 1.5                               # potenza a cui la perdita in piu' si riduce a 1/e
FASCIA_RIDUZIONE = 0.05                        # ultimo / primo 5 % della batteria: potenza ridotta
P_CMD_KW = 10.0                                # comando massimo in Third-party dispatch
P_MIN_SCARICA_KW = 2.0                         # R05: sotto 2 kW la scarica non parte (2 batterie da 2-5 kW ciascuna)
MAX_FASCE_TOU = 14
COSTO_VARIAZIONE = 0.002                       # R05: EUR per ogni cambio di comando tra ore (a parita' di ricavo: meno cambi)
STABILITA_ORE = 4                              # R05: confronto sulle 4 ore successive
STABILITA_PERC = 0.10                          #      il nuovo piano deve rendere almeno il 10 % in piu'
STABILITA_EUR = 0.10                           #      e almeno 0,10 EUR (costo di un cambio di programmazione)

THETA_INIZIALE = {"valore_finale": 1.0,        # x prezzo medio dell'orizzonte per l'energia rimasta in batteria
                  "k_scenari": 1.0,            # ampiezza degli scenari di produzione (x incertezza)
                  "peso_lati": 0.25,           # peso degli scenari bassa e alta (probabile = 1 - 2 x peso)
                  "costo_cambio": 0.0,         # EUR per cambio di modalita' tra fasce di 2 ore
                  "fz_basso": 0.35, "fz_alto": 0.65, "fz_scarica": 1.0}     # logica fuzzy
LIMITI_THETA = {"valore_finale": (0.3, 1.5), "k_scenari": (0.0, 2.5), "peso_lati": (0.0, 0.45), "costo_cambio": (0.0, 0.5),
                "fz_basso": (0.05, 0.6), "fz_alto": (0.4, 0.95), "fz_scarica": (0.2, 1.5)}


# ------------------------------------------------------------------ prezzi: noti + previsti dallo storico
def storico_prezzi():
    """{giorno 'AAAA-MM-GG': array orario NORD} da tutti i file di prezzi gia' scaricati"""
    out = {}
    pat = [os.path.join(CT.RADICE, "dati", "????-??-??", "prezzi.json"), os.path.join(CT.DATI, "prezzi", "prezzi_????????.json"),
           os.path.join(CT.OUT, "prezzi", "prezzi_????????.json")]
    for p in pat:
        for f in glob.glob(p):
            try:
                d = json.load(open(f, encoding="utf-8"))
                g = str(d.get("giorno") or "")
                g = f"{g[:4]}-{g[4:6]}-{g[6:]}" if len(g) == 8 else os.path.basename(os.path.dirname(f))
                o = [x.get("nord") for x in d.get("ore") or [] if isinstance(x, dict)]
                if len(o) >= 23 and all(isinstance(v, (int, float)) for v in o):
                    out[g] = np.array(o, dtype=float)
            except (OSError, ValueError):
                pass
    return out


def tipo_giorno(g):
    w = dt.date.fromisoformat(g).weekday()
    return "feriale" if w < 5 else ("sabato" if w == 5 else "domenica")


def prezzo_previsto(storico, g, ora):
    """prezzo NORD previsto per l'ora 'ora' (0..23) del giorno g: media pesata degli ultimi 21 giorni, piu' peso ai
    giorni dello stesso tipo (feriale/sabato/domenica) e ai piu' recenti"""
    num = den = 0.0
    d0 = dt.date.fromisoformat(g)
    for gg, v in storico.items():
        eta = (d0 - dt.date.fromisoformat(gg)).days
        if eta <= 0 or eta > 21:
            continue
        h = min(ora, len(v) - 1)
        w = 0.88 ** eta * (2.0 if tipo_giorno(gg) == tipo_giorno(g) else 1.0)
        num += w * v[h]
        den += w
    return num / den if den else None


def prezzi_orizzonte(quarti, noti):
    """prezzi per quarto d'ora: noti dove ci sono, previsti dallo storico altrove. Ritorna (prezzi, maschera_noti)"""
    st = storico_prezzi()
    pr, noto = np.zeros(len(quarti)), np.zeros(len(quarti), dtype=bool)
    ultimo = None
    for k, t in enumerate(quarti):
        if t in noti:
            pr[k], noto[k] = noti[t], True
            ultimo = noti[t]
            continue
        d = dt.datetime.fromtimestamp(t, CT.ROMA)
        p = prezzo_previsto(st, d.strftime("%Y-%m-%d"), d.hour)
        pr[k] = p if p is not None else (ultimo if ultimo is not None else 0.1)
    return pr, noto


# ------------------------------------------------------------------ struttura del piano (fasce di 2 ore, valori orari)
def struttura(quarti):
    """indici: quarto -> ora del piano, quarto -> fascia di 2 ore, quarto -> giorno; inizio di ogni ora"""
    ore, fasce, giorni = [], [], []
    mappa_o, mappa_f, mappa_g = {}, {}, {}
    for t in quarti:
        d = dt.datetime.fromtimestamp(t, CT.ROMA)
        ko = (d.strftime("%Y%m%d"), d.hour)
        kf = (d.strftime("%Y%m%d"), d.hour // 2)
        kg = d.strftime("%Y%m%d")
        ore.append(mappa_o.setdefault(ko, len(mappa_o)))
        fasce.append(mappa_f.setdefault(kf, len(mappa_f)))
        giorni.append(mappa_g.setdefault(kg, len(mappa_g)))
    return np.array(ore), np.array(fasce), np.array(giorni), len(mappa_o), len(mappa_f)


# ------------------------------------------------------------------ modello fisico non lineare (vettoriale)
def simula(modo_q, val_q, pv, prezzi, soc0, dettaglio=False, cap_kw=None):
    """modo_q, val_q: (P, N); pv: (S, N) kWh per quarto; ritorna ricavo (P, S), energia finale (P, S)
    e, con dettaglio=True (P = S = 1), le serie per quarto d'ora."""
    P, N = modo_q.shape
    S = pv.shape[0]
    LIM, PC, PS, CAP = CT.LIM_Q, CT.PC_Q, CT.PS_Q, CT.CAPACITA_KWH
    soc = np.full((P, S), float(soc0))
    eur = np.zeros((P, S))
    serie = {k: [] for k in ("carica", "scarica", "ceduto", "tagliato", "soc")} if dettaglio else None
    cap = (np.full((P, 1), PS) if cap_kw is None else (np.asarray(cap_kw, dtype=float).reshape(P, 1) * CT.Q))   # TOU: potenza max
    for k in range(N):
        f = pv[:, k][None, :]
        m = modo_q[:, k][:, None]
        v = val_q[:, k][:, None]
        pc_max = PC * np.clip((CAP - soc) / (FASCIA_RIDUZIONE * CAP), 0, 1)
        ps_max = PS * np.clip(soc / (FASCIA_RIDUZIONE * CAP), 0, 1)
        entra = (CAP - soc) / ETA_C
        esce = soc * ETA_D
        sopra = np.maximum(f - LIM, 0)
        sotto = np.maximum(LIM - f, 0)
        c_idle = np.minimum.reduce([np.broadcast_to(sopra, soc.shape), pc_max, entra])
        # Fully fed to grid
        c0 = c_idle
        s0 = np.minimum.reduce([np.broadcast_to(sotto, soc.shape), ps_max, esce])
        # TOU
        cC = np.minimum.reduce([np.broadcast_to(f, soc.shape), pc_max, entra])
        sD = np.minimum.reduce([np.broadcast_to(sotto, soc.shape), ps_max, esce])
        c1 = np.where(v > 1 / 3, cC, np.where(v < -1 / 3, 0.0, c_idle))
        s1 = np.where(v < -1 / 3, np.minimum(sD, cap), 0.0)
        # Third-party dispatch
        cmd = v * P_CMD_KW * CT.Q
        c2 = np.where(cmd > 1e-3, np.minimum.reduce([np.broadcast_to(cmd, soc.shape), np.broadcast_to(f, soc.shape), pc_max, entra]),
                      np.where(cmd < -1e-3, 0.0, c_idle))
        s2 = np.where(cmd < -1e-3, np.minimum.reduce([np.broadcast_to(-cmd, soc.shape), ps_max, esce, np.full(soc.shape, LIM)]), 0.0)
        c = np.where(m == 0, c0, np.where(m == 1, c1, c2))
        s = np.where(m == 0, s0, np.where(m == 1, s1, s2))
        c = np.maximum(c, 0)
        s = np.maximum(s, 0)
        s = np.where(s < P_MIN_SCARICA_KW * CT.Q - 1e-9, 0.0, s)        # R05: scarica minima 2 kW
        ced = np.minimum(f - c + s, LIM)
        eta_d = ETA_D * (1 - PERDITA_BASSA_POT * np.exp(-(s / CT.Q) / POT_RIF_KW))
        soc = np.clip(soc + c * ETA_C - np.where(s > 0, s / eta_d, 0.0), 0, CAP)
        eur += ced * prezzi[k]
        if dettaglio:
            for nome, x in (("carica", c), ("scarica", s), ("ceduto", ced), ("tagliato", f - c + s - ced), ("soc", soc)):
                serie[nome].append(float(x[0, 0]))
    return eur, soc, serie


def penalita(modi_f, val_o, fascia_q, ora_q, giorno_q, theta):
    """cambi di modalita' (EUR), cambi di comando tra ore (piccolo costo: a parita' di ricavo vince il piano piu' regolare)
    e fasce TOU oltre 14 al giorno (1 EUR ciascuna)"""
    cambi = (np.diff(modi_f, axis=1) != 0).sum(axis=1) * theta["costo_cambio"]
    cambi = cambi + (np.abs(np.diff(val_o, axis=1)) > 0.05).sum(axis=1) * COSTO_VARIAZIONE
    m_q = modi_f[:, fascia_q]
    lab = np.where(m_q == 1, np.where(val_o[:, ora_q] > 1 / 3, 1, np.where(val_o[:, ora_q] < -1 / 3, -1, 0)), 0)
    prec = np.concatenate([np.zeros((lab.shape[0], 1), dtype=lab.dtype), lab[:, :-1]], axis=1)
    nuovo_giorno = np.concatenate([[True], giorno_q[1:] != giorno_q[:-1]])
    inizio = (lab != 0) & ((lab != prec) | nuovo_giorno[None, :])
    extra = np.zeros(lab.shape[0])
    for g in np.unique(giorno_q):
        n = inizio[:, giorno_q == g].sum(axis=1)
        extra += np.maximum(0, n - MAX_FASCE_TOU)
    return cambi + extra * 1.0


def scenari(p50, sigma, theta):
    k, w = theta["k_scenari"], theta["peso_lati"]
    pv = np.vstack([np.maximum(0, p50 - k * sigma), p50, p50 + k * sigma])
    return pv, np.array([w, 1 - 2 * w, w])


# ------------------------------------------------------------------ semi: programmazione lineare, fuzzy, modalita' pure
def seme_lineare(p50, prezzi, soc0, ora_q, n_ore, theta):
    vf = theta["valore_finale"] * float(np.mean(prezzi))
    c, s, _ = CT.ottimo(np.asarray(p50), np.asarray(prezzi), soc0, valore_finale=vf)
    netto = c - s                                               # kWh per quarto (+ carica, - scarica)
    v = np.zeros(n_ore)
    for h in range(n_ore):
        sel = ora_q == h
        if sel.any():
            v[h] = np.clip(netto[sel].mean() / (P_CMD_KW * CT.Q), -1, 1)
    return v


def seme_fuzzy(p50, prezzi, ora_q, n_ore, theta):
    """logica fuzzy: grado 'prezzo basso', 'prezzo alto' (percentile del prezzo nell'orizzonte) e 'sole' -> comando"""
    ph = np.array([prezzi[ora_q == h].mean() for h in range(n_ore)])
    sh = np.array([p50[ora_q == h].mean() for h in range(n_ore)])
    rango = ph.argsort().argsort() / max(1, n_ore - 1)          # 0 = ora piu' economica, 1 = piu' cara
    a, b, d = theta["fz_basso"], theta["fz_alto"], theta["fz_scarica"]
    basso = np.clip(1 - rango / max(a, 1e-3), 0, 1)
    alto = np.clip((rango - b) / max(1 - b, 1e-3), 0, 1)
    sole = np.clip(sh / max(sh.max(), 1e-6), 0, 1)
    return np.clip(np.minimum(basso, sole) - d * alto, -1, 1)


# ------------------------------------------------------------------ algoritmo evolutivo
def decidi(contesto, theta, tempo_s=60.0, pop=120, max_gen=4000, stallo=300, seme=0, precedente=None):
    """contesto: quarti, p50, sigma, prezzi, soc. Ritorna il piano migliore e il riepilogo della ricerca."""
    rng = np.random.default_rng(seme)
    quarti = list(contesto["quarti"])
    p50, sigma, prezzi = (np.asarray(contesto[k], dtype=float) for k in ("p50", "sigma", "prezzi"))
    soc0 = float(contesto["soc"])
    ora_q, fascia_q, giorno_q, n_ore, n_f = struttura(quarti)
    pv, pesi = scenari(p50, sigma, theta)
    vfin = theta["valore_finale"] * float(np.mean(prezzi)) * ETA_D

    def valuta(modi_f, val_o, cap_o):
        eur, soc, _ = simula(modi_f[:, fascia_q], val_o[:, ora_q], pv, prezzi, soc0, cap_kw=cap_o)
        return (eur + soc * vfin) @ pesi - penalita(modi_f, val_o, fascia_q, ora_q, giorno_q, theta)

    v_lin = seme_lineare(p50, prezzi, soc0, ora_q, n_ore, theta)
    v_fz = seme_fuzzy(p50, prezzi, ora_q, n_ore, theta)
    semi = {"lineare - Third-party": (2, v_lin), "lineare - TOU": (1, v_lin), "Fully fed to grid": (0, np.zeros(n_ore)),
            "fuzzy - Third-party": (2, v_fz), "fuzzy - TOU": (1, v_fz)}
    M = [np.full(n_f, m) for m, _ in semi.values()]
    V = [v.copy() for _, v in semi.values()]
    nomi_semi = list(semi)
    C = [P_CMD_KW] * len(M)
    if precedente:                                              # piano precedente, sulle ore ancora valide
        mp, vp, cp = np.full(n_f, 2), v_lin.copy(), P_CMD_KW
        for k, t in enumerate(quarti):
            x = precedente.get(str(t))
            if x:
                mp[fascia_q[k]] = x[0]
                vp[ora_q[k]] = x[1]
                cp = x[2] if len(x) > 2 else cp
        M.append(mp); V.append(vp); C.append(cp); nomi_semi.append("piano precedente")
    while len(M) < pop:                                         # varianti dei semi e casuali
        i = rng.integers(0, len(nomi_semi))
        if rng.random() < 0.7:
            mm = M[i].copy(); vv = np.clip(V[i] + rng.normal(0, 0.3, n_ore), -1, 1)
            cambia = rng.random(n_f) < 0.2
            mm[cambia] = rng.integers(0, 3, int(cambia.sum()))
        else:
            mm = rng.integers(0, 3, n_f); vv = rng.uniform(-1, 1, n_ore)
        M.append(mm); V.append(vv); C.append(float(rng.uniform(P_MIN_SCARICA_KW, P_CMD_KW)))
    Mp, Vp, Cp = np.array(M), np.array(V), np.array(C, dtype=float)
    fit = valuta(Mp, Vp, Cp)
    punteggi_semi = {n: round(float(fit[i]), 3) for i, n in enumerate(nomi_semi)}
    t0 = time.perf_counter()
    gen, ultimo_migl, migliore = 0, 0, float(fit.max())
    while gen < max_gen and time.perf_counter() - t0 < tempo_s and gen - ultimo_migl < stallo:
        gen += 1
        def torneo():
            a = rng.integers(0, pop, (pop, 3))
            return a[np.arange(pop), fit[a].argmax(axis=1)]
        p1, p2 = torneo(), torneo()
        mf = np.where(rng.random((pop, n_f)) < 0.5, Mp[p1], Mp[p2])
        vf = np.where(rng.random((pop, n_ore)) < 0.5, Vp[p1], Vp[p2])
        mut = rng.random((pop, n_f)) < 0.06
        mf = np.where(mut, rng.integers(0, 3, (pop, n_f)), mf)
        mv = rng.random((pop, n_ore)) < 0.15
        vf = np.clip(vf + mv * rng.normal(0, 0.25, (pop, n_ore)), -1, 1)
        cf = np.where(rng.random(pop) < 0.5, Cp[p1], Cp[p2])
        cf = np.clip(cf + (rng.random(pop) < 0.2) * rng.normal(0, 1.5, pop), P_MIN_SCARICA_KW, P_CMD_KW)
        ff = valuta(mf, vf, cf)
        tutti_m, tutti_v, tutti_c = np.vstack([Mp, mf]), np.vstack([Vp, vf]), np.concatenate([Cp, cf])
        tutti_f = np.concatenate([fit, ff])
        keep = np.argsort(-tutti_f)[:pop]                       # (genitori + figli): restano i migliori
        Mp, Vp, Cp, fit = tutti_m[keep], tutti_v[keep], tutti_c[keep], tutti_f[keep]
        if fit.max() > migliore + 1e-6:
            migliore, ultimo_migl = float(fit.max()), gen
    b = int(fit.argmax())
    modi_f, val_o, cap = Mp[b], Vp[b], round(float(Cp[b]), 2)
    piano = {str(t): [int(modi_f[fascia_q[k]]), round(float(val_o[ora_q[k]]), 4), cap] for k, t in enumerate(quarti)}
    return {"piano": piano, "atteso_eur": round(migliore, 3), "punteggi_semi": punteggi_semi, "generazioni": gen,
            "valutazioni": pop * (gen + 1), "secondi": round(time.perf_counter() - t0, 1),
            "fasce": riassunto(quarti, piano)}


def riassunto(quarti, piano):
    """testo: modalita' per fascia di 2 ore e fasce TOU"""
    out, cur = [], None
    for t in quarti:
        m, v = piano[str(t)][:2]
        cap = piano[str(t)][2] if len(piano[str(t)]) > 2 else P_CMD_KW
        if m == 1:
            et = "carica" if v > 1 / 3 else (f"scarica (max {cap:.1f} kW)" if v < -1 / 3 else "nessuna fascia")
            nome = f"TOU {et}"
        elif m == 2:
            p = v * P_CMD_KW
            nome = "Third-party " + ("carica %.1f kW" % p if p > 0.05 else ("scarica %.1f kW" % -p if p <= -P_MIN_SCARICA_KW else "fermo"))
        else:
            nome = "Fully fed to grid"
        if cur and cur[0] == nome:
            cur[2] = t + 900
        else:
            if cur:
                out.append(cur)
            cur = [nome, t, t + 900]
    if cur:
        out.append(cur)
    h = lambda t: dt.datetime.fromtimestamp(t, CT.ROMA).strftime("%d/%m %H:%M")
    return [f"{h(a)}-{h(b)[-5:]} {n}" for n, a, b in out]


def esegui_quarto(modo, val, pv, soc, cap_kw=P_CMD_KW):
    """un quarto d'ora reale con il modello non lineare: (carica, scarica, ceduto, tagliato, soc_dopo)"""
    eur, s2, ser = simula(np.array([[modo]]), np.array([[val]]), np.array([[pv]]), np.array([0.0]), soc, dettaglio=True,
                          cap_kw=[cap_kw])
    return ser["carica"][0], ser["scarica"][0], ser["ceduto"][0], ser["tagliato"][0], ser["soc"][0]


def carica_theta():
    d = {}
    try:
        d = json.load(open(os.path.join(CT.OUT, "live", "apprendimento.json"), encoding="utf-8")).get("theta") or {}
    except (OSError, ValueError):
        pass
    th = dict(THETA_INIZIALE)
    th.update({k: float(v) for k, v in d.items() if k in th})
    return th


def stabilita(contesto, theta, nuovo, vecchio):
    """R05: si cambia il piano gia' spedito solo se il nuovo, nelle prossime 4 ore, genera almeno il 10 % in piu' e almeno
    0,10 EUR. Confronto con i dati nuovi (3 scenari) su tutto l'orizzonte tra: A = piano nuovo; B = piano spedito per le
    prossime 4 ore e poi piano nuovo. Cosi' l'energia messa in batteria nelle 4 ore vale quanto rendera' dopo.
    Soglia: max(0,10 EUR; 10 % del ricavo delle 4 ore del piano spedito). Ritorna (piano da usare, informazioni)."""
    tutti = list(contesto["quarti"])
    quattro = tutti[:STABILITA_ORE * 4]
    if not vecchio or not quattro or any(str(t) not in vecchio for t in quattro):
        return nuovo, {"cambio": True, "motivo": "nessun piano precedente valido per le prossime 4 ore"}
    ibrido = dict(nuovo)
    ibrido.update({str(t): vecchio[str(t)] for t in quattro})
    p50, sigma, prezzi = (np.asarray(contesto[k], dtype=float) for k in ("p50", "sigma", "prezzi"))
    pv, pesi = scenari(p50, sigma, theta)
    vfin = theta["valore_finale"] * float(np.mean(prezzi)) * ETA_D

    def arr(piano):
        x = [piano[str(t)] for t in tutti]
        return ([m for m, *_ in x], [v for _, v, *_ in x], [(y[2] if len(y) > 2 else P_CMD_KW) for y in x])
    mA, vA, cA = arr(nuovo)
    mB, vB, cB = arr(ibrido)
    # potenza TOU: una per piano (la prima ora del piano)
    eur, soc, _ = simula(np.array([mA, mB]), np.array([vA, vB]), pv, prezzi, float(contesto["soc"]), cap_kw=[cA[0], cB[0]])
    val = (eur + soc * vfin) @ pesi
    n4 = len(quattro)
    e4, _, _ = simula(np.array([mB[:n4]]), np.array([vB[:n4]]), pv[:, :n4], prezzi[:n4], float(contesto["soc"]), cap_kw=[cB[0]])
    ricavo4_vecchio = float(e4[0] @ pesi)
    guadagno = float(val[0] - val[1])
    soglia = max(STABILITA_EUR, STABILITA_PERC * abs(ricavo4_vecchio))
    info = {"guadagno_eur": round(guadagno, 3), "soglia_eur": round(soglia, 3), "ricavo_4h_piano_spedito_eur": round(ricavo4_vecchio, 3)}
    if guadagno >= soglia:
        return nuovo, dict(info, cambio=True, motivo="il nuovo piano rende abbastanza di piu' grazie alle prossime 4 ore")
    return ibrido, dict(info, cambio=False, motivo="guadagno sotto la soglia: per le prossime 4 ore resta il piano spedito")
