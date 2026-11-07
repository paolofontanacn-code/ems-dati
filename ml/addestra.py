# -*- coding: utf-8 -*-
# Revisione R08 - 07/11/2026 - verifica di modello completo e logica fuzzy con il METEO PREVISTO (richieste del Mango,
#   come le previsioni del Mango); fuzzy con consumi delle ore dei giorni prima (scelti se aiutano); indice di bravura
#   giornaliero e frequenza dei carichi ripetitivi nel riepilogo modelli/consumi_fuzzy.json
# Revisione R07 - 31/10/2026 - terzo modello dei consumi: logica fuzzy autoapprendente (ml/consumi_fuzzy.py), confrontato
#   con le previsioni del Mango e con il modello completo: per le decisioni si usa quello che sbaglia meno; stime fuzzy
#   giornaliere per la pagina (previsioni/fuzzy/AAAA-MM-GG.json) e riepilogo modelli/consumi_fuzzy.json
"""
addestra.py - machine learning su GitHub per l'EMS di Cismondi (SOLO SIMULAZIONE)

Legge i dati del repository (storico FusionSolar del giorno 0 e dataset giornalieri del programma Mango) e:
  1. addestra due modelli completi (gradient boosting): consumi della casa e produzione FV, a quarti d'ora;
  2. ricalcola i coefficienti nel formato del Mango (profili per tipo di giorno, pompa di calore, resa FV);
  3. verifica entrambi sugli ultimi 7 giorni contro le previsioni che il Mango aveva fatto davvero:
     un modello viene ACCETTATO solo se sbaglia meno;
  4. per ogni richiesta di previsione del Mango (richieste/richiesta_AAAAMMGG.json) scrive
     previsioni/prev_AAAAMMGG.json con consumi e FV previsti per ogni quarto d'ora.
  5. (R07) stima dei consumi con logica fuzzy autoapprendente e automigliorante (consumi_fuzzy.py), verificata come gli
     altri: nelle previsioni per il Mango i consumi vengono dal modello che sbaglia meno, se sbaglia meno del Mango.
Uscite: modelli/coefficienti_mango.json, previsioni/prev_*.json, modelli/ULTIMO_ADDESTRAMENTO.md,
        modelli/consumi_fuzzy.json, previsioni/fuzzy/AAAA-MM-GG.json
"""
import datetime as dt
import glob
import gzip
import json
import math
import os
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import consumi_fuzzy as FZ  # noqa: E402

RADICE = os.environ.get("EMS_REPO_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROMA = ZoneInfo("Europe/Rome")
P_NOMINALE_FV = 11000.0
P_MAX_PDC = 3000.0
TB_RISC, TB_RAFF = 18.0, 24.0
GRUPPO = {"feriale": "lavoro", "ponte": "lavoro", "sabato": "sabato", "domenica": "festa", "festivo": "festa"}
TIPI = ["feriale", "ponte", "sabato", "domenica", "festivo"]
GIORNI_PROVA = 7
MARGINE_ACCETTAZIONE = 0.97        # il nuovo modello deve sbagliare almeno il 3 % in meno


def log(msg):
    print(f"{dt.datetime.now():%H:%M:%S}  {msg}", flush=True)


# ------------------------------------------------------------------ calendario (stesse regole del Mango)
def pasqua(a):
    A, B, C = a % 19, a // 100, a % 100
    D, E = B // 4, B % 4
    F = (B + 8) // 25
    G = (B - F + 1) // 3
    H = (19 * A + B - D - G + 15) % 30
    I, K = C // 4, C % 4
    L = (32 + 2 * E + 2 * I - H - K) % 7
    M = (A + 11 * H + 22 * L) // 451
    return dt.date(a, (H + L - 7 * M + 114) // 31, (H + L - 7 * M + 114) % 31 + 1)


def festivo(d):
    if (d.month, d.day) in {(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)}:
        return True
    if d.year >= 2026 and (d.month, d.day) == (10, 4):
        return True
    p = pasqua(d.year)
    return d in (p, p + dt.timedelta(days=1))


def tipo_giorno(d):
    w = d.weekday()            # 0 = lunedi'
    if w == 6:
        return "domenica"
    if festivo(d):
        return "festivo"
    if w == 5:
        return "sabato"
    def fest_o_weekend(x):
        return x.weekday() >= 5 or festivo(x)
    prima, dopo = d - dt.timedelta(days=1), d + dt.timedelta(days=1)
    if (festivo(prima) and prima.weekday() < 5 and fest_o_weekend(dopo)) or \
       (festivo(dopo) and dopo.weekday() < 5 and fest_o_weekend(prima)):
        return "ponte"
    return "feriale"


_cache_tipo = {}


def aggiungi_calendario(df):
    loc = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert(ROMA)
    df["data"] = loc.dt.date
    df["ora"] = loc.dt.hour
    df["qo"] = loc.dt.hour * 4 + loc.dt.minute // 15 + 1          # quarto d'ora dell'orologio 1..96
    df["settimana"] = loc.dt.weekday + 1
    df["mese"] = loc.dt.month
    df["doy"] = loc.dt.dayofyear
    tipi = []
    for d in df["data"]:
        if d not in _cache_tipo:
            _cache_tipo[d] = tipo_giorno(d)
        tipi.append(_cache_tipo[d])
    df["tipo"] = tipi
    df["tipo_c"] = df["tipo"].map({t: i for i, t in enumerate(TIPI)})
    return df


def caratteristiche_pdc(temp_lag, vento, ghi):
    hdd = np.maximum(0, TB_RISC - temp_lag)
    return np.vstack([hdd, hdd * hdd / 10, hdd * vento / 10, hdd * ghi / 1000, np.maximum(0, temp_lag - TB_RAFF)]).T


# ------------------------------------------------------------------ dati
def leggi_csv(nome):
    if nome.endswith(".gz"):
        with gzip.open(nome, "rt", encoding="utf-8") as f:
            return pd.read_csv(f)
    return pd.read_csv(nome)


def meteo_storico():
    serie = {}
    for f in glob.glob(os.path.join(RADICE, "storico", "meteo_*.json")):
        with open(f, encoding="utf-8") as h:
            for k, v in json.load(h).items():
                serie[int(k)] = v
    return serie


def meteo_per(ts, serie):
    """stesse regole del Mango: temperatura e nuvole interpolate, irraggiamento = media dell'ora che finisce dopo."""
    out = {"temp": [], "temp_lag": [], "nuvole": [], "ghi": [], "vento": []}
    for t in ts:
        h0 = t // 3600 * 3600
        a, b = serie.get(h0), serie.get(h0 + 3600)
        if a is None and b is None:
            for k in out:
                out[k].append(np.nan)
            continue
        a, b = a or b, b or a
        f = (t - h0) / 3600
        def interp(k):
            va, vb = a.get(k), b.get(k)
            if va is None or vb is None:
                return va if vb is None else vb
            return va + (vb - va) * f
        out["temp"].append(interp("temp"))
        out["nuvole"].append(interp("nuvole"))
        out["vento"].append(interp("vento"))
        out["ghi"].append(b.get("ghi", a.get("ghi")))
        temps = [serie[h0 - k * 3600]["temp"] for k in range(4) if serie.get(h0 - k * 3600, {}).get("temp") is not None]
        out["temp_lag"].append(sum(temps) / len(temps) if temps else np.nan)
    return pd.DataFrame(out)


def carica_dati():
    parti = []
    file_sto = sorted(glob.glob(os.path.join(RADICE, "storico", "storico_*.csv*")))
    if file_sto:
        sto = pd.concat([leggi_csv(f) for f in file_sto], ignore_index=True)
        sto = sto.dropna(subset=["ts", "carico_w"]).drop_duplicates("ts")
        sto["ts"] = sto["ts"].astype(np.int64)
        met = meteo_per(sto["ts"].to_numpy(), meteo_storico())
        sto = pd.concat([sto[["ts", "carico_w", "fv_w"]].reset_index(drop=True), met], axis=1)
        sto["fonte"] = "storico"
        parti.append(sto)
    file_ds = sorted(glob.glob(os.path.join(RADICE, "dati", "*", "dataset.csv*")))
    for f in file_ds:
        d = leggi_csv(f)
        if "carico_w" not in d:
            continue
        d = d[d["carico_w"].notna()]
        x = pd.DataFrame({"ts": d["ts"].astype(np.int64), "carico_w": d["carico_w"], "fv_w": d["fv_w"],
                          "temp": d.get("temp_c"), "temp_lag": d.get("temp_lag3h_c"), "nuvole": d.get("nuvole"),
                          "ghi": d.get("ghi_wm2"), "vento": d.get("vento"),
                          "prev_carico_sera": d.get("prev_carico_sera_w"), "prev_fv_sera": d.get("prev_fv_sera_w"),
                          "prev_carico_mod": d.get("prev_carico_w"), "prev_fv_mod": d.get("prev_fv_w")})
        x["fonte"] = "simulazione"
        parti.append(x)
    if not parti:
        return None
    df = pd.concat(parti, ignore_index=True)
    df = df.sort_values(["ts", "fonte"]).drop_duplicates("ts", keep="last")
    # media per quarto d'ora
    df["tq"] = df["ts"] // 900 * 900
    num = [c for c in df.columns if c not in ("fonte", "tq", "ts")]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    q = df.groupby("tq")[num].mean().reset_index().rename(columns={"tq": "ts"})
    q = aggiungi_calendario(q)
    q["temp_lag"] = q["temp_lag"].fillna(q["temp"])
    return q


FEAT_CARICO = ["qo", "settimana", "tipo_c", "mese", "temp", "temp_lag", "hdd", "ghi", "nuvole", "vento"]
FEAT_FV = ["qo", "doy", "ghi", "nuvole", "temp"]


def prepara(df):
    df = df.copy()
    df["hdd"] = np.maximum(0, TB_RISC - df["temp_lag"])
    return df


def modello():
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, l2_regularization=1.0, random_state=1)


# ------------------------------------------------------------------ formato Mango
def coefficienti_mango(df):
    """profili per tipo e quarto d'ora, coefficienti pompa di calore (minimi quadrati vincolati), resa FV."""
    d = df.dropna(subset=["temp_lag", "carico_w"]).copy()
    if d.empty:
        return None
    d["vento"] = d["vento"].fillna(0)
    d["ghi"] = d["ghi"].fillna(0)
    X = caratteristiche_pdc(d["temp_lag"].to_numpy(), d["vento"].to_numpy(), d["ghi"].to_numpy())
    for i in range(5):
        d[f"x{i}"] = X[:, i]
    g = d.groupby("data").agg(carico=("carico_w", "mean"), n=("carico_w", "size"), tipo=("tipo", "first"),
                              **{f"x{i}": (f"x{i}", "mean") for i in range(5)})
    g = g[g["n"] >= 70]
    if len(g) < 10:
        return None
    g = g.tail(120)
    A = np.zeros((len(g), 8))
    for k, t in enumerate(g["tipo"]):
        A[k, ["lavoro", "sabato", "festa"].index(GRUPPO[t])] = 1
    for i in range(5):
        A[:, 3 + i] = g[f"x{i}"].to_numpy()
    w = 0.99 ** np.arange(len(g) - 1, -1, -1)
    sw = np.sqrt(w)
    ris = lsq_linear(A * sw[:, None], g["carico"].to_numpy() * sw,
                     bounds=([0, 0, 0, 0, 0, 0, -500, 0], [np.inf, np.inf, np.inf, 1000, 500, 500, 0, 1000]))
    theta = ris.x[3:]
    pdc = np.clip(X @ theta, 0, P_MAX_PDC)
    d["comp"] = np.maximum(0, d["carico_w"].to_numpy() - pdc)
    recenti = d[d["data"] >= (d["data"].max() - dt.timedelta(days=60))]
    profili = {}
    for t in TIPI:
        x = recenti[recenti["tipo"] == t]
        if len(x) >= 96:
            profili[t] = {str(int(k)): float(v) for k, v in x.groupby("qo")["comp"].mean().items()}
    fv = df.dropna(subset=["ghi", "fv_w"])
    fv = fv[fv["ghi"] > 50].copy()
    fv["coef"] = np.clip(fv["fv_w"] / (fv["ghi"] / 1000 * P_NOMINALE_FV), 0, 1.3)
    fv["cls"] = np.where(fv["nuvole"].fillna(50) < 30, 1, np.where(fv["nuvole"].fillna(50) < 70, 2, 3))
    fv_coef = {}
    for (ora, cls), x in fv.groupby(["ora", "cls"]):
        if len(x) >= 6:
            fv_coef.setdefault(str(int(ora)), [None, None, None])[int(cls) - 1] = float(x["coef"].median())
    return {"profili": profili, "theta": [float(v) for v in theta], "livelli": [float(v) for v in ris.x[:3]], "fv_coef": fv_coef}


def prevedi_mango(coef, df):
    """previsione con la formula del Mango (profilo del tipo di giorno + pompa di calore; FV = coefficiente x GHI)."""
    X = caratteristiche_pdc(df["temp_lag"].fillna(df["temp"]).to_numpy(), df["vento"].fillna(0).to_numpy(), df["ghi"].fillna(0).to_numpy())
    pdc = np.clip(X @ np.array(coef["theta"]), 0, P_MAX_PDC)
    comp = []
    for t, q in zip(df["tipo"], df["qo"]):
        p = coef["profili"].get(t) or next((coef["profili"][x] for x in TIPI if GRUPPO[x] == GRUPPO[t] and x in coef["profili"]), None) \
            or next(iter(coef["profili"].values()), {})
        comp.append(p.get(str(int(q)), np.nan))
    car = np.array(comp) + pdc
    cls = np.where(df["nuvole"].fillna(50) < 30, 1, np.where(df["nuvole"].fillna(50) < 70, 2, 3))
    cf = []
    for ora, c in zip(df["ora"], cls):
        v = coef["fv_coef"].get(str(int(ora)), [None, None, None])
        val = v[c - 1] if v[c - 1] is not None else next((x for x in v if x is not None), 0.8)
        cf.append(val)
    fv = np.minimum(P_NOMINALE_FV, np.array(cf) * df["ghi"].fillna(0).to_numpy() / 1000 * P_NOMINALE_FV)
    return car, fv


def mae(a, b):
    m = ~(np.isnan(a) | np.isnan(b))
    return float(np.mean(np.abs(a[m] - b[m]))) if m.any() else None


# ------------------------------------------------------------------ R07: logica fuzzy, file per la pagina
DIR_FUZZY = os.path.join(RADICE, "previsioni", "fuzzy")


def iso(g):
    return f"{g[:4]}-{g[4:6]}-{g[6:8]}"


def con_meteo_richieste(test):
    """R08: i quarti di prova con il meteo PREVISTO la sera prima (richieste/richiesta_AAAAMMGG.json del Mango);
    dove la richiesta manca resta il meteo del dataset. Ritorna (quadro, quarti con meteo previsto)"""
    x = test.copy()
    n = 0
    for d in sorted(x["data"].unique()):
        f = os.path.join(RADICE, "richieste", f"richiesta_{d.strftime('%Y%m%d')}.json")
        if not os.path.exists(f):
            continue
        try:
            with open(f, encoding="utf-8") as h:
                q = {int(v["ts"]): v for v in json.load(h).get("quarti", [])}
        except (OSError, ValueError):
            continue
        for i in x.index[x["data"] == d]:
            v = q.get(int(x.at[i, "ts"]))
            if not v or v.get("temp") is None:
                continue
            x.at[i, "temp"] = v["temp"]
            x.at[i, "temp_lag"] = v.get("temp_lag3h", v["temp"])
            for k_d, k_r in (("ghi", "ghi"), ("nuvole", "nuvole"), ("vento", "vento")):
                if v.get(k_r) is not None:
                    x.at[i, k_d] = v[k_r]
            n += 1
    return prepara(x), n


def quadro_richiesta(r):
    q = pd.DataFrame(r.get("quarti", []))
    x = aggiungi_calendario(pd.DataFrame({"ts": q["ts"].astype(np.int64)}))
    x["temp"] = pd.to_numeric(q.get("temp"), errors="coerce")
    x["ghi"] = pd.to_numeric(q.get("ghi"), errors="coerce")
    x["carico_w"] = np.nan
    return x


def stima_fuzzy_richiesta(mod, df, r):
    x = quadro_richiesta(r)
    storia = df[df["ts"] < x["ts"].min()]
    return FZ.stima(mod, storia, x)


def salva_fuzzy(giorno_iso, inizio, valori, fonte, extra=None):
    os.makedirs(DIR_FUZZY, exist_ok=True)
    d = {"giorno": giorno_iso, "inizio": int(inizio), "passo_s": 900, "carico_w": [None if v is None else round(float(v), 1) for v in valori],
         "fonte": fonte, "generato_il": dt.datetime.now(ROMA).isoformat(timespec="minutes")}
    d.update(extra or {})
    with open(os.path.join(DIR_FUZZY, giorno_iso + ".json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def scrivi_fuzzy(mod, df, r, g, oggi):
    """stima del giorno prima: si aggiorna fino all'inizio del giorno, poi resta quella (il giorno in corso solo se manca)"""
    dest = os.path.join(DIR_FUZZY, iso(g) + ".json")
    if g == oggi and os.path.exists(dest):
        return
    x = quadro_richiesta(r)
    p = stima_fuzzy_richiesta(mod, df, r)
    fonte = "stima del giorno prima (meteo previsto)" if g > oggi else "stima calcolata a giorno iniziato (meteo previsto)"
    salva_fuzzy(iso(g), x["ts"].min(), [p.get(int(t)) for t in x["ts"]], fonte,
                {"inerzia_ore": mod["inerzia_ore"], "oblio": mod["oblio"], "ritardi": mod.get("ritardi", False)})


def rigioca_fuzzy(df, inerzia, oblio, oggi, max_giorni=7, indietro=60, ritardi=False):
    """giorni passati senza stima: addestramento sui soli giorni prima e meteo misurato (fuori campione);
    errore medio dei giorni passati gia' stimati"""
    giorni = sorted(df["data"].unique())[-indietro:]
    fatti = 0
    for d in reversed(giorni):                    # prima i giorni piu' recenti
        g = d.strftime("%Y%m%d")
        if g >= oggi:
            continue
        dest = os.path.join(DIR_FUZZY, iso(g) + ".json")
        reale = df[df["data"] == d]
        if os.path.exists(dest):
            try:
                with open(dest, encoding="utf-8") as h:
                    v = json.load(h)
                if v.get("mae_w") is None and len(reale) >= 72:
                    mappa = {v["inizio"] + k * v["passo_s"]: x for k, x in enumerate(v["carico_w"])}
                    v["mae_w"] = FZ.mae([mappa.get(int(t), np.nan) if mappa.get(int(t)) is not None else np.nan for t in reale["ts"]],
                                        reale["carico_w"].to_numpy(dtype=float))
                    v["mae_w"] = None if v["mae_w"] is None else round(v["mae_w"], 1)
                    with open(dest, "w", encoding="utf-8") as h:
                        json.dump(v, h, ensure_ascii=False)
            except (OSError, ValueError):
                pass
            continue
        if fatti >= max_giorni or len(reale) < 72:
            continue
        prima = df[df["data"] < d]
        mod = FZ.addestra(prima, inerzia, oblio, ritardi)
        if mod is None:
            continue
        t0 = int(pd.Timestamp(d).tz_localize(ROMA).timestamp())
        n = int(round((pd.Timestamp(d + dt.timedelta(days=1)).tz_localize(ROMA).timestamp() - t0) / 900))
        x = aggiungi_calendario(pd.DataFrame({"ts": [t0 + k * 900 for k in range(n)]}))
        x = x.merge(reale[["ts", "temp", "ghi"]], on="ts", how="left")
        x["temp"] = x["temp"].interpolate(limit_direction="both")
        x["ghi"] = x["ghi"].fillna(0)
        x["carico_w"] = np.nan
        p = FZ.stima(mod, prima, x)
        val = [p.get(int(t)) for t in x["ts"]]
        e = FZ.mae([np.nan if v is None else v for v in [p.get(int(t)) for t in reale["ts"]]], reale["carico_w"].to_numpy(dtype=float))
        salva_fuzzy(iso(g), t0, val, "ricalcolata dopo, sui soli giorni prima e con il meteo misurato",
                    {"inerzia_ore": inerzia, "oblio": oblio, "mae_w": None if e is None else round(e, 1)})
        fatti += 1
    if fatti:
        log(f"Stime fuzzy rigiocate per {fatti} giorni passati")


def bravura(df, giorni=60):
    """R08: indice di bravura giornaliero della stima fuzzy = 1 - errore fuzzy / errore di riferimento.
    Riferimenti: previsioni del Mango registrate (sera prima) e "stesso giorno della settimana prima" (consumo reale
    degli stessi quarti d'ora 7 giorni prima). Indice > 0: la fuzzy sbaglia meno del riferimento. Se nel tempo l'indice
    sale, il sistema impara (non dipende dal livello dei consumi della stagione)."""
    out = []
    reale = df.set_index("ts")["carico_w"]
    for f in sorted(glob.glob(os.path.join(DIR_FUZZY, "*.json")))[-giorni:]:
        try:
            with open(f, encoding="utf-8") as h:
                v = json.load(h)
        except (OSError, ValueError):
            continue
        ts = [v["inizio"] + k * v["passo_s"] for k in range(len(v["carico_w"]))]
        r = np.array([reale.get(t, np.nan) for t in ts], dtype=float)
        if np.isfinite(r).sum() < 72:
            continue
        fz = np.array([np.nan if x is None else x for x in v["carico_w"]], dtype=float)
        sett = np.array([reale.get(t - 7 * 86400, np.nan) for t in ts], dtype=float)
        d = df[df["ts"].isin(ts)]
        mango = d.set_index("ts")["prev_carico_sera"].reindex(ts).to_numpy(dtype=float) if "prev_carico_sera" in d else np.full(len(ts), np.nan)
        e_fz, e_s, e_m = mae(fz, r), mae(sett, r), (mae(mango, r) if np.isfinite(mango).sum() >= 48 else None)
        out.append({"giorno": v["giorno"], "fonte": v.get("fonte"), "mae_fuzzy": e_fz, "mae_settimana_prima": e_s, "mae_mango": e_m,
                    "indice_vs_mango": None if (e_fz is None or not e_m) else 1 - e_fz / e_m,
                    "indice_vs_settimana_prima": None if (e_fz is None or not e_s) else 1 - e_fz / e_s})
    for k in ("indice_vs_mango", "indice_vs_settimana_prima"):          # media degli ultimi 7 giorni con il valore
        for i, x in enumerate(out):
            v7 = [y[k] for y in out[max(0, i - 6):i + 1] if y[k] is not None]
            x[k + "_media7"] = float(np.mean(v7)) if v7 else None
    rnd = lambda v: None if v is None else round(float(v), 3)
    return [{k: (rnd(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in x.items()} for x in out]


def salva_riepilogo_fuzzy(fz, mod, esito, scelta, df=None):
    f = os.path.join(RADICE, "modelli", "consumi_fuzzy.json")
    try:
        with open(f, encoding="utf-8") as h:
            st = json.load(h)
    except (OSError, ValueError):
        st = {}
    rnd = lambda v: None if v is None else round(float(v), 1)
    ver = {"giorni": GIORNI_PROVA, "mae_fuzzy": rnd(fz.get("mae_carico")), "mae_mango": rnd(fz.get("mae_carico_mango")),
           "mae_ml": rnd(esito["ml"].get("mae_carico")), "scelta": scelta, "accettata": bool(fz.get("accettato")),
           "motivo": fz.get("motivo")}
    storico = (st.get("storico") or [])[-300:]
    storico.append({"quando": dt.datetime.now(ROMA).isoformat(timespec="minutes"), **ver,
                    "inerzia_ore": fz.get("inerzia_ore"), "oblio": fz.get("oblio"), "ritardi": fz.get("ritardi")})
    st.update({"revisione": "R07", "aggiornato": dt.datetime.now(ROMA).isoformat(timespec="minutes"), "verifica": ver,
               "parametri": {"inerzia_ore": fz.get("inerzia_ore"), "oblio": fz.get("oblio"), "ore_dei_giorni_prima": fz.get("ritardi")},
               "prove_automiglioramento": fz.get("prove", []), "storico": storico,
               "incidenze": FZ.incidenze(mod) if mod else None,
               "bravura": bravura(df) if df is not None else [],
               "carichi_ripetitivi": FZ.carichi_ripetitivi(df) if df is not None else None})
    with open(f, "w", encoding="utf-8") as h:
        json.dump(st, h, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ principale
def main():
    os.makedirs(os.path.join(RADICE, "modelli"), exist_ok=True)
    os.makedirs(os.path.join(RADICE, "previsioni"), exist_ok=True)
    df = carica_dati()
    if df is None or len(df) < 96 * 3:
        log("Dati insufficienti per l'addestramento: niente da fare")
        return 0
    df = prepara(df)
    giorni = sorted(df["data"].unique())
    log(f"Dati: {len(df)} quarti d'ora, {len(giorni)} giorni ({giorni[0]} - {giorni[-1]})")
    righe_md = [f"# Ultimo addestramento - {dt.datetime.now(ROMA):%d/%m/%Y %H:%M}", "",
                f"Dati: {len(df)} quarti d'ora su {len(giorni)} giorni ({giorni[0]} - {giorni[-1]}).", ""]

    # finestra di prova: ultimi giorni con previsioni del Mango registrate
    prova_giorni = [g for g in giorni[-GIORNI_PROVA:]]
    test = df[df["data"].isin(prova_giorni)]
    train = df[~df["data"].isin(prova_giorni)]
    rif_car = test["prev_carico_sera"].fillna(test["prev_carico_mod"]) if "prev_carico_sera" in test else None
    test_prev, n_prev = con_meteo_richieste(test)          # R08: verifica con il meteo previsto la sera prima
    righe_md.append(f"Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in {n_prev} quarti d'ora su {len(test)}; "
                    "negli altri il meteo del dataset (quello usato dal Mango in quel momento).")
    righe_md.append("")
    rif_fv = test["prev_fv_sera"].fillna(test["prev_fv_mod"]) if "prev_fv_sera" in test else None
    ha_rif = rif_car is not None and rif_car.notna().sum() >= 96

    esito = {"ml": {"accettato": False, "motivo": ""}, "mango": {"accettato": False, "motivo": ""}}
    tc = train.dropna(subset=FEAT_CARICO + ["carico_w"])
    tf = train.dropna(subset=FEAT_FV + ["fv_w"])
    if len(tc) < 96 * 10 or not ha_rif:
        msg = "servono almeno 10 giorni di addestramento e 1 giorno con previsioni del Mango per il confronto"
        esito["ml"]["motivo"] = esito["mango"]["motivo"] = msg
        righe_md.append(f"Verifica non possibile: {msg}.")
    else:
        mc = modello().fit(tc[FEAT_CARICO], tc["carico_w"])
        mf = modello().fit(tf[FEAT_FV], tf["fv_w"]) if len(tf) > 200 else None
        tt = test_prev.dropna(subset=FEAT_CARICO)
        p_car = mc.predict(tt[FEAT_CARICO])
        e_ml = mae(p_car, tt["carico_w"].to_numpy())
        e_rif = mae(rif_car.loc[tt.index].to_numpy(dtype=float), tt["carico_w"].to_numpy())
        tfv = test_prev.dropna(subset=FEAT_FV)
        e_ml_fv = mae(np.clip(mf.predict(tfv[FEAT_FV]), 0, P_NOMINALE_FV), tfv["fv_w"].to_numpy()) if mf is not None and len(tfv) else None
        e_rif_fv = mae(rif_fv.loc[tfv.index].to_numpy(dtype=float), tfv["fv_w"].to_numpy()) if len(tfv) else None
        acc = e_ml is not None and e_rif is not None and e_ml < e_rif * MARGINE_ACCETTAZIONE
        esito["ml"] = {"accettato": bool(acc), "mae_carico": e_ml, "mae_carico_mango": e_rif, "mae_fv": e_ml_fv,
                       "mae_fv_mango": e_rif_fv, "motivo": "migliore delle previsioni del Mango" if acc else "non migliore del Mango"}
        coef_t = coefficienti_mango(train)
        if coef_t:
            pc, pf = prevedi_mango(coef_t, test_prev)
            e_m = mae(pc, test["carico_w"].to_numpy())
            acc_m = e_m is not None and e_rif is not None and e_m < e_rif * MARGINE_ACCETTAZIONE
            esito["mango"] = {"accettato": bool(acc_m), "mae_carico": e_m, "mae_carico_mango": e_rif,
                              "motivo": "coefficienti migliori di quelli in uso" if acc_m else "non migliori di quelli in uso"}
        else:
            esito["mango"]["motivo"] = "dati giornalieri insufficienti (servono 10 giorni completi)"
        righe_md += ["| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |", "|---|---|---|---|",
                     f"| Previsioni del Mango (registrate) | {e_rif and round(e_rif)} | {e_rif_fv and round(e_rif_fv)} | riferimento |",
                     f"| Modello completo (GitHub) | {e_ml and round(e_ml)} | {e_ml_fv and round(e_ml_fv)} | {'ACCETTATO' if acc else 'non accettato'} |",
                     f"| Coefficienti formato Mango | {esito['mango'].get('mae_carico') and round(esito['mango']['mae_carico'])} | - | "
                     f"{'ACCETTATI' if esito['mango']['accettato'] else 'non accettati'} |", ""]

    # ---------------- R07: logica fuzzy (autoapprendimento + automiglioramento sugli stessi giorni di prova)
    fz = {"accettato": False, "motivo": "", "mae_carico": None}
    try:
        migliore, prove = FZ.scegli(train, test, test_prev) if len(train.dropna(subset=["carico_w"])) >= 96 * 5 else (None, [])
        if migliore:
            e_fz, iner, obl, rit = migliore
            e_rif_fz = mae(rif_car.to_numpy(dtype=float), test["carico_w"].to_numpy()) if ha_rif else None
            acc_fz = e_rif_fz is not None and e_fz < e_rif_fz * MARGINE_ACCETTAZIONE
            fz = {"accettato": bool(acc_fz), "mae_carico": e_fz, "mae_carico_mango": e_rif_fz, "inerzia_ore": iner, "oblio": obl, "ritardi": rit,
                  "prove": prove, "motivo": ("migliore delle previsioni del Mango" if acc_fz else
                                              ("non migliore del Mango" if e_rif_fz is not None else "previsioni del Mango non disponibili per il confronto"))}
            riga = f"| Logica fuzzy (inerzia casa {iner} h, oblio {obl}{', ore dei giorni prima' if rit else ''}) | {round(e_fz)} | - | {'ACCETTATA' if acc_fz else 'non accettata'} |"
            if righe_md and righe_md[-1] == "" and righe_md[-2].startswith("|"):
                righe_md.insert(len(righe_md) - 1, riga)        # dentro la tabella della verifica
            else:
                righe_md.append(riga)
        else:
            fz["motivo"] = "dati insufficienti (servono almeno 5 giorni di addestramento)"
    except Exception as ex:                                   # la stima fuzzy non deve fermare il resto
        fz["motivo"] = f"errore: {ex}"
        log(f"Logica fuzzy: errore {ex}")
    esito["fuzzy"] = {k: v for k, v in fz.items() if k != "prove"}
    # modello dei consumi per le decisioni del Mango: il migliore tra quelli accettati (altrimenti le previsioni del Mango)
    cand = []
    if esito["ml"].get("accettato"):
        cand.append(("modello completo", esito["ml"]["mae_carico"]))
    if fz.get("accettato"):
        cand.append(("logica fuzzy", fz["mae_carico"]))
    scelta_carico = min(cand, key=lambda x: x[1])[0] if cand else "previsioni del Mango"
    righe_md.append(f"Consumi per le decisioni: {scelta_carico}.")
    log(f"Consumi per le decisioni: {scelta_carico}")

    # coefficienti finali (tutti i dati) e modelli finali
    coef = coefficienti_mango(df)
    uscita = {"versione": dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M"), "generato_il": dt.datetime.now(ROMA).isoformat(),
              "accettato": bool(esito["mango"]["accettato"] and coef), "motivo": esito["mango"]["motivo"], "verifica": esito}
    if coef:
        uscita.update(coef)
        righe_md.append("Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): " +
                        ", ".join(f"{v:.1f}" for v in coef["theta"]))
    with open(os.path.join(RADICE, "modelli", "coefficienti_mango.json"), "w", encoding="utf-8") as f:
        json.dump(uscita, f, ensure_ascii=False, indent=1)

    # previsioni richieste dal Mango
    tutti_c = df.dropna(subset=FEAT_CARICO + ["carico_w"])
    tutti_f = df.dropna(subset=FEAT_FV + ["fv_w"])
    mc_all = modello().fit(tutti_c[FEAT_CARICO], tutti_c["carico_w"]) if len(tutti_c) > 96 * 3 else None
    mf_all = modello().fit(tutti_f[FEAT_FV], tutti_f["fv_w"]) if len(tutti_f) > 200 else None
    mod_fz = None
    try:
        if fz.get("inerzia_ore") is not None:
            mod_fz = FZ.addestra(df, fz["inerzia_ore"], fz["oblio"], fz.get("ritardi", False))
    except Exception as ex:
        log(f"Logica fuzzy (modello finale): errore {ex}")
    oggi = dt.datetime.now(ROMA).strftime("%Y%m%d")
    for f in sorted(glob.glob(os.path.join(RADICE, "richieste", "richiesta_*.json"))):
        g = os.path.basename(f)[len("richiesta_"):-len(".json")]
        dest = os.path.join(RADICE, "previsioni", f"prev_{g}.json")
        if g < oggi:
            continue
        with open(f, encoding="utf-8") as h:
            r0 = json.load(h)
        if mod_fz is not None:
            try:
                scrivi_fuzzy(mod_fz, df, r0, g, oggi)
            except Exception as ex:
                log(f"Stima fuzzy per {g}: errore {ex}")
        if os.path.exists(dest):
            # si rifa' solo se la versione precedente non era stata accettata
            try:
                with open(dest, encoding="utf-8") as h:
                    if json.load(h).get("accettato"):
                        continue
            except (OSError, ValueError):
                pass
        with open(f, encoding="utf-8") as h:
            r = json.load(h)
        q = pd.DataFrame(r.get("quarti", []))
        out = {"giorno": g, "accettato": False, "motivo": esito["ml"]["motivo"] or "modello non disponibile",
               "generato_il": dt.datetime.now(ROMA).isoformat(), "carico_w": {}, "fv_w": {}, "modello_carico": scelta_carico}
        if scelta_carico == "logica fuzzy" and mod_fz is not None and len(q):
            # R07: consumi dalla logica fuzzy; FV dal modello completo solo se accettato
            pfz = stima_fuzzy_richiesta(mod_fz, df, r)
            out["carico_w"] = {str(int(qq)): round(float(pfz[int(t)]), 1) for qq, t in zip(q["q"], q["ts"]) if int(t) in pfz}
            out["accettato"] = bool(out["carico_w"])
            out["motivo"] = "consumi: logica fuzzy (" + fz["motivo"] + ")"
            if mf_all is not None and esito["ml"].get("accettato"):
                x = aggiungi_calendario(pd.DataFrame({"ts": q["ts"]}))
                x["temp"], x["ghi"], x["nuvole"] = q.get("temp"), q.get("ghi"), q.get("nuvole")
                okf = x[FEAT_FV].notna().all(axis=1)
                pf = np.full(len(x), np.nan)
                pf[okf.to_numpy()] = np.clip(mf_all.predict(x.loc[okf, FEAT_FV]), 0, P_NOMINALE_FV)
                pf[(x["ghi"].fillna(0) <= 0).to_numpy()] = 0
                out["fv_w"] = {str(int(qq)): round(float(pf[k]), 1) for k, qq in enumerate(q["q"]) if not math.isnan(pf[k])}
        elif mc_all is not None and len(q):
            x = pd.DataFrame({"ts": q["ts"]})
            x = aggiungi_calendario(x)
            x["temp"] = q.get("temp")
            x["temp_lag"] = q.get("temp_lag3h", q.get("temp"))
            x["temp_lag"] = x["temp_lag"].fillna(x["temp"])
            x["ghi"], x["nuvole"], x["vento"] = q.get("ghi"), q.get("nuvole"), q.get("vento")
            x = prepara(x)
            ok = x[FEAT_CARICO].notna().all(axis=1)
            pc = np.full(len(x), np.nan)
            pc[ok.to_numpy()] = mc_all.predict(x.loc[ok, FEAT_CARICO])
            pf = np.full(len(x), np.nan)
            okf = x[FEAT_FV].notna().all(axis=1)
            if mf_all is not None:
                pf[okf.to_numpy()] = np.clip(mf_all.predict(x.loc[okf, FEAT_FV]), 0, P_NOMINALE_FV)
                pf[(x["ghi"].fillna(0) <= 0).to_numpy()] = 0
            for k, qq in enumerate(q["q"]):
                if not math.isnan(pc[k]):
                    out["carico_w"][str(int(qq))] = round(float(max(0, pc[k])), 1)
                if not math.isnan(pf[k]):
                    out["fv_w"][str(int(qq))] = round(float(pf[k]), 1)
            out["accettato"] = bool(esito["ml"]["accettato"])
            if scelta_carico == "previsioni del Mango":
                out["carico_w"] = {}                              # R07: consumi del Mango (sbagliano meno)
        with open(dest, "w", encoding="utf-8") as h:
            json.dump(out, h, ensure_ascii=False)
        log(f"Previsioni per {g}: {'accettate' if out['accettato'] else 'non accettate'} ({out['motivo']})")
        righe_md.append(f"Previsioni per {g}: {'accettate' if out['accettato'] else 'non accettate'} ({out['motivo']}).")

    # R07: stime fuzzy dei giorni passati (rigiocate fuori campione, per la pagina) e riepilogo
    if fz.get("inerzia_ore") is not None:
        try:
            rigioca_fuzzy(df, fz["inerzia_ore"], fz["oblio"], oggi, ritardi=fz.get("ritardi", False))
        except Exception as ex:
            log(f"Stime fuzzy dei giorni passati: errore {ex}")
    try:
        salva_riepilogo_fuzzy(fz, mod_fz, esito, scelta_carico, df)
    except Exception as ex:
        log(f"Riepilogo fuzzy: errore {ex}")

    with open(os.path.join(RADICE, "modelli", "ULTIMO_ADDESTRAMENTO.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(righe_md) + "\n")
    log("Addestramento completato")
    return 0


if __name__ == "__main__":
    sys.exit(main())
