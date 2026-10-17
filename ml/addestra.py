"""
addestra.py - machine learning su GitHub per l'EMS di Cismondi (SOLO SIMULAZIONE)

Legge i dati del repository (storico FusionSolar del giorno 0 e dataset giornalieri del programma Mango) e:
  1. addestra due modelli completi (gradient boosting): consumi della casa e produzione FV, a quarti d'ora;
  2. ricalcola i coefficienti nel formato del Mango (profili per tipo di giorno, pompa di calore, resa FV);
  3. verifica entrambi sugli ultimi 7 giorni contro le previsioni che il Mango aveva fatto davvero:
     un modello viene ACCETTATO solo se sbaglia meno;
  4. per ogni richiesta di previsione del Mango (richieste/richiesta_AAAAMMGG.json) scrive
     previsioni/prev_AAAAMMGG.json con consumi e FV previsti per ogni quarto d'ora.
Uscite: modelli/coefficienti_mango.json, previsioni/prev_*.json, modelli/ULTIMO_ADDESTRAMENTO.md
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
        tt = test.dropna(subset=FEAT_CARICO)
        p_car = mc.predict(tt[FEAT_CARICO])
        e_ml = mae(p_car, tt["carico_w"].to_numpy())
        e_rif = mae(rif_car.loc[tt.index].to_numpy(dtype=float), tt["carico_w"].to_numpy())
        tfv = test.dropna(subset=FEAT_FV)
        e_ml_fv = mae(np.clip(mf.predict(tfv[FEAT_FV]), 0, P_NOMINALE_FV), tfv["fv_w"].to_numpy()) if mf is not None and len(tfv) else None
        e_rif_fv = mae(rif_fv.loc[tfv.index].to_numpy(dtype=float), tfv["fv_w"].to_numpy()) if len(tfv) else None
        acc = e_ml is not None and e_rif is not None and e_ml < e_rif * MARGINE_ACCETTAZIONE
        esito["ml"] = {"accettato": bool(acc), "mae_carico": e_ml, "mae_carico_mango": e_rif, "mae_fv": e_ml_fv,
                       "mae_fv_mango": e_rif_fv, "motivo": "migliore delle previsioni del Mango" if acc else "non migliore del Mango"}
        coef_t = coefficienti_mango(train)
        if coef_t:
            pc, pf = prevedi_mango(coef_t, test)
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
    for f in sorted(glob.glob(os.path.join(RADICE, "richieste", "richiesta_*.json"))):
        g = os.path.basename(f)[len("richiesta_"):-len(".json")]
        dest = os.path.join(RADICE, "previsioni", f"prev_{g}.json")
        if g < dt.datetime.now(ROMA).strftime("%Y%m%d"):
            continue
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
               "generato_il": dt.datetime.now(ROMA).isoformat(), "carico_w": {}, "fv_w": {}}
        if mc_all is not None and len(q):
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
        with open(dest, "w", encoding="utf-8") as h:
            json.dump(out, h, ensure_ascii=False)
        log(f"Previsioni per {g}: {'accettate' if out['accettato'] else 'non accettate'} ({out['motivo']})")
        righe_md.append(f"Previsioni per {g}: {'accettate' if out['accettato'] else 'non accettate'} ({out['motivo']}).")

    with open(os.path.join(RADICE, "modelli", "ULTIMO_ADDESTRAMENTO.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(righe_md) + "\n")
    log("Addestramento completato")
    return 0


if __name__ == "__main__":
    sys.exit(main())
