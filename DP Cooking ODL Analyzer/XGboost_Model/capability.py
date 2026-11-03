"""
Operating Window by capability.

Question: "In which combined range of X does Y (Viscosity) have the best Cpk?"

Pipeline:   Capability  ->  Operating Window  ->  Critical X Combination
  1. baseline(df)            Cpk of Viscosity over all batches (the number to beat)
  2. search(df)              grid search: split each X into CAP_BINS quantile bins, try every
                             combination of CAP_COMBO_SIZE X, score Cpk of the batches in each box
  3. report(df, rules)       Cpk / mean / std / N  inside the best window vs outside

No PI access: reads the same data as golden.py (batch_master.csv) via golden.load_golden().
Cpk assumes Viscosity is roughly normal inside a box; skewness is printed as a warning.
Small boxes (N < CAP_MIN_N) are dropped because their Cpk is unreliable.
"""

from itertools import combinations, product

import numpy as np
import pandas as pd
from scipy.stats import skew

import config
import golden


# ---------------------------------------------------------------- capability
def cpk(y, spec=None):
    """Cpk of a 1-D array against (LSL, USL). NaN when < 2 points or SD == 0."""
    lsl, usl = spec or config.CAP_SPEC
    y = np.asarray(y, dtype=float)
    y = y[~np.isnan(y)]
    if len(y) < 2:
        return np.nan
    mu, sd = y.mean(), y.std(ddof=1)
    if sd == 0:
        return np.nan
    return min((usl - mu) / (3 * sd), (mu - lsl) / (3 * sd))


def cp(y, spec=None):
    """Cp (potential capability, ignores centering)."""
    lsl, usl = spec or config.CAP_SPEC
    y = np.asarray(y, dtype=float)
    y = y[~np.isnan(y)]
    if len(y) < 2:
        return np.nan
    sd = y.std(ddof=1)
    return (usl - lsl) / (6 * sd) if sd > 0 else np.nan


def _stats(y, spec=None):
    y = np.asarray(y, dtype=float)
    y = y[~np.isnan(y)]
    return {
        "n": len(y),
        "mean": y.mean() if len(y) else np.nan,
        "std": y.std(ddof=1) if len(y) > 1 else np.nan,
        "cpk": cpk(y, spec),
        "cp": cp(y, spec),
    }


def _stats2(sub):
    """Capability of BOTH Y on the same batches. sub is a DataFrame with the two target columns.
    cpk_min = min(cpk_visc, cpk_kappa) = the worse of the two = how well the window holds both."""
    yv = sub[config.CAP_TARGET]
    yk = sub[config.CAP_TARGET2]
    n = int(yv.notna().sum())
    cpk_v = cpk(yv, config.CAP_SPEC)
    cpk_k = cpk(yk, config.CAP_SPEC2)
    return {
        "n": n,
        "visc_mean": yv.mean(),
        "cp_visc": cp(yv, config.CAP_SPEC),
        "cpk_visc": cpk_v,
        "kappa_mean": yk.mean(),
        "cp_kappa": cp(yk, config.CAP_SPEC2),
        "cpk_kappa": cpk_k,
        "cpk_min": np.nanmin([cpk_v, cpk_k]) if not (np.isnan(cpk_v) and np.isnan(cpk_k)) else np.nan,
    }


def baseline(df=None):
    """Capability of BOTH Y over every batch = the numbers any window must beat."""
    df = golden.load_golden() if df is None else df
    s = _stats2(df)
    lv, uv = config.CAP_SPEC
    lk, uk = config.CAP_SPEC2
    print(f"baseline: N={s['n']}  "
          f"Viscosity mean={s['visc_mean']:.1f} Cpk={s['cpk_visc']:.2f} (spec {lv}-{uv})  |  "
          f"Kappa mean={s['kappa_mean']:.1f} Cpk={s['cpk_kappa']:.2f} (spec {lk}-{uk})  |  "
          f"Cpk_min={s['cpk_min']:.2f}")
    for name, col, sp in (("Viscosity", config.CAP_TARGET, config.CAP_SPEC),
                          ("Kappa", config.CAP_TARGET2, config.CAP_SPEC2)):
        y = df[col].dropna()
        sk = skew(y) if len(y) > 2 else np.nan
        if abs(sk) > 1:
            print(f"  WARNING: {name} is skewed (|skew|={abs(sk):.2f} > 1); read Cpk as a guide.")
    return s


def baseline_by_digester(df=None):
    """Cpk of Viscosity per digester (D1-D4) + overall. Answers: is the spread a
    'which pot' effect or a real process effect? No X binning, so N stays large."""
    df = golden.load_golden() if df is None else df
    if "digester" not in df.columns:
        print("no 'digester' column in the data; cannot split by digester.")
        return pd.DataFrame()
    rows = []
    for dg, g in df.groupby("digester"):
        rows.append({"digester": dg, **_stats2(g)})
    rows.append({"digester": "ALL", **_stats2(df)})
    res = pd.DataFrame(rows)
    num = res.select_dtypes("number").columns
    res[num] = res[num].round(2)
    lv, uv = config.CAP_SPEC
    lk, uk = config.CAP_SPEC2
    print(f"baseline by digester (Viscosity {lv}-{uv}, Kappa {lk}-{uk}):")
    return res


# ---------------------------------------------------------------- binning
# A few X are categorical (e.g. digester = 1,2,3,4): bin them as-is, not by quantile.
CAP_CATEGORICAL = {"digester"}


def _bins(df, x, bins=None):
    """Bin one X into a Categorical aligned to df.index. Quantile bins for numeric X;
    the raw values for categorical X (digester). NaN where X is NaN."""
    bins = bins or config.CAP_BINS
    if x in CAP_CATEGORICAL:
        return df[x].astype("category")
    return pd.qcut(df[x], bins, duplicates="drop")


def _fmt(key):
    """Label for a bin key: 'lo-hi' for a numeric Interval, else the value itself."""
    return f"{key.left:.2f}-{key.right:.2f}" if isinstance(key, pd.Interval) else str(key)


def _rule(x, key):
    """A filter rule (col, lo, hi) for report(). Categorical value v -> (col, v, v)."""
    if isinstance(key, pd.Interval):
        return (x, float(key.left), float(key.right))
    return (x, key, key)


def _bin_table(df, x, bins=None):
    """One X on its own: Cpk of BOTH Y per bin (quick look before combining)."""
    sub = df[[x, config.CAP_TARGET, config.CAP_TARGET2]].dropna(subset=[x, config.CAP_TARGET])
    g = _bins(sub, x, bins)
    rows = []
    for key, idx in sub.groupby(g, observed=True).groups.items():
        s = _stats2(sub.loc[idx])
        rows.append({"x": config.CAP_X.get(x, x), "range": _fmt(key), **s})
    res = pd.DataFrame(rows)
    num = res.select_dtypes("number").columns
    res[num] = res[num].round(2)
    return res


def bin_tables(df=None):
    """Per-X single-variable Cpk table for each X in CAP_X (sanity check)."""
    df = golden.load_golden() if df is None else df
    out = {x: _bin_table(df, x) for x in config.CAP_X if x in df.columns}
    return out


# ---------------------------------------------------------------- grid search
def search(df=None, combo_size=None, bins=None, min_n=None):
    """
    Grid search. For every combination of `combo_size` X, split each into `bins` quantile bins and
    score the batches in each box by cpk_min = min(Cpk_visc, Cpk_kappa). Returns boxes with
    N >= min_n, ranked by cpk_min (best first). Each row is one Critical X Combination.
    """
    df = golden.load_golden() if df is None else df
    combo_size = combo_size or config.CAP_COMBO_SIZE
    bins = bins or config.CAP_BINS
    min_n = min_n or config.CAP_MIN_N
    xs = [x for x in config.CAP_X if x in df.columns and df[x].notna().sum() > 0]

    rows = []
    for combo in combinations(xs, combo_size):
        sub = df.dropna(subset=list(combo) + [config.CAP_TARGET, config.CAP_TARGET2]).copy()
        if len(sub) < min_n:
            continue
        cats = {x: _bins(sub, x, bins) for x in combo}
        levels = [list(cats[x].cat.categories) for x in combo]
        for cells in product(*levels):
            mask = pd.Series(True, index=sub.index)
            for x, interval in zip(combo, cells):
                mask &= (cats[x] == interval)
            if mask.sum() < min_n:
                continue
            s = _stats2(sub.loc[mask])
            row = {"combo": " x ".join(config.CAP_X.get(x, x) for x in combo)}
            for x, key in zip(combo, cells):
                row[config.CAP_X.get(x, x)] = _fmt(key)
            row.update(s)
            row["rules"] = [_rule(x, key) for x, key in zip(combo, cells)]
            rows.append(row)

    res = pd.DataFrame(rows)
    if res.empty:
        print(f"no box with N >= {min_n}; lower CAP_MIN_N or CAP_BINS, or CAP_COMBO_SIZE.")
        return res
    res = res.sort_values("cpk_min", ascending=False).reset_index(drop=True)
    print(f"search: {len(res)} boxes with N >= {min_n}  (combo size {combo_size}, {bins} bins/X, "
          f"ranked by cpk_min)")
    return res


def summary(res, top=10):
    """Readable top-N table of search(): the combination, its range, N, and Cpk of both Y."""
    if res.empty:
        return res
    metrics = ("n", "visc_mean", "cpk_visc", "kappa_mean", "cpk_kappa", "cpk_min")
    x_cols = [c for c in res.columns if c not in ("combo", "rules") + metrics]
    cols = ["combo"] + x_cols + ["n", "cpk_visc", "cpk_kappa", "cpk_min"]
    out = res.head(top)[cols].copy()
    for c in ("cpk_visc", "cpk_kappa", "cpk_min"):
        out[c] = out[c].round(2)
    return out


# ---------------------------------------------------------------- report
def report(df=None, rules=None):
    """
    Inside vs outside the window. rules = [(column, lo, hi), ...]; a batch is INSIDE when every X
    is within its [lo, hi]. Defaults to the best box from search(). Prints Cpk/mean/std/N for both.
    """
    df = golden.load_golden() if df is None else df
    if rules is None:
        res = search(df)
        if res.empty:
            return None
        rules = res.iloc[0]["rules"]
        parts = []
        for c, lo, hi in rules:
            label = config.CAP_X.get(c, c)
            parts.append(f"{label} {lo}" if lo == hi else f"{label} {lo:.2f}-{hi:.2f}")
        print("best window:", ", ".join(parts))

    sub = df.dropna(subset=[c for c, _, _ in rules] + [config.CAP_TARGET, config.CAP_TARGET2]).copy()
    inside = pd.Series(True, index=sub.index)
    for col, lo, hi in rules:
        inside &= sub[col].between(lo, hi)

    out = pd.DataFrame({"inside": _stats2(sub.loc[inside]),
                        "outside": _stats2(sub.loc[~inside])}).T
    out["n"] = out["n"].astype(int)
    print(out.round({"visc_mean": 1, "cpk_visc": 2,
                     "kappa_mean": 1, "cpk_kappa": 2, "cpk_min": 2}).to_string())
    return out
