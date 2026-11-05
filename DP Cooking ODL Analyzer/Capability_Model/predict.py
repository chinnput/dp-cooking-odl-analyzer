"""
predict.py  --  score a FINISHED batch against the historical capability boxes.

Idea (not a trained model, a lookup):
  1. search() builds `res` = a table of boxes. Each box = a rule list
     [(X, lo, hi), ...] + the mean Viscosity / Kappa and Cp of the batches in it.
  2. score(res, x) takes one batch's X (after discharge, so every X is final),
     finds every box whose rules the batch satisfies, and returns those boxes
     sorted by cp_min -- "this batch lands in these windows, so expect this Y".
  3. backtest() checks the idea on history (leave-one-out): predict each golden
     batch from the boxes built WITHOUT it, compare to its real lab Y.

No model file is saved: the "model" is `res`, which you rebuild from golden any
time with search(). No PI access here -- x comes from you (dict / csv / the
realtime_pi helper).
"""

import numpy as np
import pandas as pd

import config
import golden
import capability as cap


# ------------------------------------------------------------------ helpers
def _batch_in_box(x, rules):
    """True if batch dict `x` satisfies every rule (col, lo, hi). Missing X -> not in box."""
    for col, lo, hi in rules:
        v = x.get(col)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return False
        if not (lo <= v <= hi):
            return False
    return True


def _label_to_key(x_labelled):
    """Accept X keyed by short label ('P-temp SP') OR by column name. Return column-keyed dict."""
    label2col = {lbl: col for col, lbl in config.CAP_X.items()}
    out = {}
    for k, v in x_labelled.items():
        out[label2col.get(k, k)] = v
    return out


# ------------------------------------------------------------------ score
def score(res, x, top=None):
    """
    Which boxes does this finished batch fall into, and what Y do they imply?

    res : table from cap.search() (the "model").
    x   : one batch's X. dict keyed by batch_master column OR short label, e.g.
          {"pfactor_overshoot": 40, "P-temp SP": 165, "digester": 3}.
          Only the X used by a box need to be present for that box to match.
    top : keep only the best `top` matching boxes (by cp_min). None = all.

    Returns a DataFrame of matching boxes (combo, range, n, cp_min, visc_pred,
    kappa_pred, ...), best cp first. Use consensus(result) for a single number.
    """
    if res is None or res.empty:
        print("empty res; run cap.search() first.")
        return pd.DataFrame()
    xc = _label_to_key(x)
    rows = []
    for _, r in res.iterrows():
        if _batch_in_box(xc, r["rules"]):
            rows.append({
                "combo": r["combo"],
                "rules": _rule_text(r["rules"]),
                "n": int(r["n"]),
                "visc_pred": round(r["visc_mean"], 1),
                "kappa_pred": round(r["kappa_mean"], 2),
                "cp_visc": round(r["cp_visc"], 2),
                "cp_kappa": round(r["cp_kappa"], 2),
                "cp_min": round(r["cp_min"], 2),
            })
    out = pd.DataFrame(rows)
    if out.empty:
        print("this batch falls into NO historical box (new operating region, or missing X).")
        return out
    out = out.sort_values("cp_min", ascending=False).reset_index(drop=True)
    if top:
        out = out.head(top)
    return out


def _rule_text(rules):
    """'pfactor_overshoot 20-40, digester 3' -- human-readable rule, short labels."""
    parts = []
    for col, lo, hi in rules:
        lbl = config.CAP_X.get(col, col)
        parts.append(f"{lbl} {lo:g}" if lo == hi else f"{lbl} {lo:g}-{hi:g}")
    return ", ".join(parts)


def consensus(scored):
    """
    One prediction from all matching boxes, weighted by N (bigger box = more trust).
    Returns a dict: visc_pred, kappa_pred, cp_min (worst of the matched boxes = the
    honest risk), n_boxes, n_batches.
    """
    if scored is None or scored.empty:
        return {"visc_pred": np.nan, "kappa_pred": np.nan, "cp_min": np.nan,
                "n_boxes": 0, "n_batches": 0}
    w = scored["n"].to_numpy(dtype=float)
    return {
        "visc_pred": round(float(np.average(scored["visc_pred"], weights=w)), 1),
        "kappa_pred": round(float(np.average(scored["kappa_pred"], weights=w)), 2),
        "cp_min": round(float(scored["cp_min"].min()), 2),   # worst box = honest floor
        "n_boxes": int(len(scored)),
        "n_batches": int(scored["n"].sum()),
    }


def predict(x, df=None, combo_size=None, bins=None, min_n=None, top=None, by_digester=True):
    """
    Convenience: build res from golden and score x in one call.
    by_digester=True builds res from only the same-digester history (if x has a digester),
    which matches how by_digester() is used -- a D3 batch is judged against D3 boxes.
    Returns (scored_table, consensus_dict).
    """
    df = golden.load_golden() if df is None else df
    xc = _label_to_key(x)
    dg = xc.get("digester")
    if by_digester and dg is not None and "digester" in df.columns:
        sub = df[df["digester"] == dg]
        xs = [c for c in config.CAP_X if c != "digester"]
        res = cap.search(sub, combo_size=combo_size, bins=bins, min_n=min_n, xs=xs)
    else:
        res = cap.search(df, combo_size=combo_size, bins=bins, min_n=min_n)
    scored = score(res, x, top=top)
    return scored, consensus(scored)


# ------------------------------------------------------------------ backtest
def backtest(df=None, combo_size=None, bins=None, min_n=None, by_digester=True):
    """
    Leave-one-out check of the lookup idea on history.
    For each golden batch: build res from all OTHER batches, score the batch,
    take the consensus prediction, compare to its real lab Y.

    Prints MAE of Viscosity & Kappa vs the naive baseline (predict the global
    mean every time) and the hit rate (prediction within spec AND real within
    spec -> agree). A useful method beats the baseline MAE.
    """
    df = (golden.load_golden() if df is None else df).reset_index(drop=True)
    xs_cols = list(config.CAP_X)
    need = xs_cols + [config.CAP_TARGET, config.CAP_TARGET2]
    df = df.dropna(subset=[config.CAP_TARGET, config.CAP_TARGET2]).reset_index(drop=True)

    vis_true, vis_pred, kap_true, kap_pred, covered = [], [], [], [], 0
    for i in range(len(df)):
        train = df.drop(index=i)
        row = df.loc[i]
        x = {c: row[c] for c in xs_cols if c in df.columns}
        dg = x.get("digester")
        if by_digester and dg is not None:
            sub = train[train["digester"] == dg]
            xs = [c for c in xs_cols if c != "digester"]
            res = cap.search(sub, combo_size=combo_size, bins=bins, min_n=min_n, xs=xs)
        else:
            res = cap.search(train, combo_size=combo_size, bins=bins, min_n=min_n)
        c = consensus(score(res, x))
        if c["n_boxes"] == 0 or np.isnan(c["visc_pred"]):
            continue
        covered += 1
        vis_true.append(row[config.CAP_TARGET]); vis_pred.append(c["visc_pred"])
        kap_true.append(row[config.CAP_TARGET2]); kap_pred.append(c["kappa_pred"])

    n = len(df)
    if covered == 0:
        print("backtest: no batch fell into any box; lower min_n/combo_size.")
        return {}
    vis_true, vis_pred = np.array(vis_true), np.array(vis_pred)
    kap_true, kap_pred = np.array(kap_true), np.array(kap_pred)
    mae_v = np.mean(np.abs(vis_true - vis_pred))
    mae_k = np.mean(np.abs(kap_true - kap_pred))
    base_v = np.mean(np.abs(vis_true - vis_true.mean()))   # predict-the-mean baseline
    base_k = np.mean(np.abs(kap_true - kap_true.mean()))

    def in_spec(y, sp):
        return (y >= sp[0]) & (y <= sp[1])
    agree = np.mean(in_spec(vis_pred, config.CAP_SPEC) == in_spec(vis_true, config.CAP_SPEC))

    print(f"backtest (leave-one-out, by_digester={by_digester}):")
    print(f"  covered {covered}/{n} batches ({covered/n:.0%}) fell into >=1 box")
    print(f"  Viscosity MAE {mae_v:6.1f}  vs baseline {base_v:6.1f}  "
          f"({'BETTER' if mae_v < base_v else 'worse'})")
    print(f"  Kappa     MAE {mae_k:6.2f}  vs baseline {base_k:6.2f}  "
          f"({'BETTER' if mae_k < base_k else 'worse'})")
    print(f"  Viscosity in/out-of-spec agreement: {agree:.0%}")
    return {"covered": covered, "n": n, "mae_visc": mae_v, "base_visc": base_v,
            "mae_kappa": mae_k, "base_kappa": base_k, "spec_agreement": agree}
