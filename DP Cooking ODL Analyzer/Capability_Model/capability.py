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
    cp_v = cp(yv, config.CAP_SPEC)
    cp_k = cp(yk, config.CAP_SPEC2)
    cpk_v = cpk(yv, config.CAP_SPEC)
    cpk_k = cpk(yk, config.CAP_SPEC2)
    return {
        "n": n,
        "visc_mean": yv.mean(),
        "cp_visc": cp_v,
        "cpk_visc": cpk_v,
        "kappa_mean": yk.mean(),
        "cp_kappa": cp_k,
        "cpk_kappa": cpk_k,
        "cp_min": np.nanmin([cp_v, cp_k]) if not (np.isnan(cp_v) and np.isnan(cp_k)) else np.nan,
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


def _bins(df, x, bins=None, edges=None):
    """Bin one X into a Categorical aligned to df.index. Categorical X (digester) keep their raw
    values. Numeric X use `edges` (fixed cut points) when given, else quantile bins. NaN stays NaN."""
    bins = bins or config.CAP_BINS
    if x in CAP_CATEGORICAL:
        return df[x].astype("category")
    if edges is not None:
        return pd.cut(df[x], edges, include_lowest=True)
    return pd.qcut(df[x], bins, duplicates="drop")


def _global_edges(df, xs, bins=None):
    """Compute bin edges for each numeric X ONCE from the full df, so every combo shares the same
    ranges. Uses CAP_FIXED_EDGES when provided for an X, else global quantile (qcut) edges."""
    bins = bins or config.CAP_BINS
    edges = {}
    for x in xs:
        if x in CAP_CATEGORICAL:
            continue
        fixed = config.CAP_FIXED_EDGES.get(x)
        if fixed is not None:
            edges[x] = list(fixed)
        else:
            cats = pd.qcut(df[x], bins, duplicates="drop")
            e = [cats.cat.categories[0].left] + [iv.right for iv in cats.cat.categories]
            edges[x] = e
    return edges


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
def search(df=None, combo_size=None, bins=None, min_n=None, xs=None):
    """
    Grid search. For every combination of `combo_size` X, split each into `bins` quantile bins and
    score the batches in each box by cp_min = min(Cp_visc, Cp_kappa). Returns boxes with
    N >= min_n, ranked by cp_min (best first). Each row is one Critical X Combination.
    `xs` overrides which X are searched (default = all of config.CAP_X).
    """
    df = golden.load_golden() if df is None else df
    combo_size = combo_size or config.CAP_COMBO_SIZE
    bins = bins or config.CAP_BINS
    min_n = min_n or config.CAP_MIN_N
    xs = xs or list(config.CAP_X)
    xs = [x for x in xs if x in df.columns and df[x].notna().sum() > 0]
    edges = _global_edges(df, xs, bins)  # fixed, comparable bin edges across every combo

    rows = []
    for combo in combinations(xs, combo_size):
        sub = df.dropna(subset=list(combo) + [config.CAP_TARGET, config.CAP_TARGET2]).copy()
        if len(sub) < min_n:
            continue
        cats = {x: _bins(sub, x, bins, edges.get(x)) for x in combo}
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
    res = res.sort_values("cp_min", ascending=False).reset_index(drop=True)
    print(f"search: {len(res)} boxes with N >= {min_n}  (combo size {combo_size}, {bins} bins/X, "
          f"ranked by cp_min)")
    return res


def summary(res, top=10):
    """Readable top-N table of search(): the combination, its range, N, and Cpk of both Y."""
    if res.empty:
        return res
    metrics = ("n", "visc_mean", "cp_visc", "cpk_visc", "kappa_mean", "cp_kappa", "cpk_kappa",
               "cp_min", "cpk_min")
    present = [c for c in res.columns if c not in ("combo", "rules") + metrics]
    x_cols = [config.CAP_X[k] for k in config.CAP_X if config.CAP_X[k] in present]
    x_cols += [c for c in present if c not in x_cols]        # any extra, keep at the end
    cols = ["combo"] + x_cols + ["n", "cp_kappa", "cp_visc", "cpk_kappa", "cpk_visc", "cp_min", "cpk_min"]
    out = res.head(top)[cols].copy()
    for c in ("cp_kappa", "cp_visc", "cpk_kappa", "cpk_visc", "cp_min", "cpk_min"):
        out[c] = out[c].round(2)
    for c in x_cols:                                          # X not in the combo -> show "-" not NaN
        out[c] = out[c].astype(object).where(out[c].notna(), "-")
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


# ---------------------------------------------------------------- sensitivity
def sensitivity(df=None, res=None, rank=0, combo_size=None, bins=None, min_n=None):
    """
    One-factor-at-a-time around a chosen box. Takes the box at `rank` from search() (default best),
    holds every X but one at its chosen range, and slides that one X across every bin it really took.
    Columns match summary() (all X of the combo, n, cp/cpk): the held X repeat their chosen range,
    the slid X changes row to row. The row index marks the slid X and '< chosen' / 'small-n'.
    """
    df = golden.load_golden() if df is None else df
    combo_size = combo_size or config.CAP_COMBO_SIZE
    bins = bins or config.CAP_BINS
    min_n = min_n or config.CAP_MIN_N
    if res is None:
        res = search(df, combo_size, bins, min_n)
    if res.empty:
        return res

    rules = res.iloc[rank]["rules"]                         # [(col, lo, hi), ...] of the chosen box
    combo = [c for c, _, _ in rules]
    xs = [x for x in config.CAP_X if x in df.columns and df[x].notna().sum() > 0]
    edges = _global_edges(df, xs, bins)

    sub = df.dropna(subset=combo + [config.CAP_TARGET, config.CAP_TARGET2]).copy()
    cats = {x: _bins(sub, x, bins, edges.get(x)) for x in combo}
    chosen = {}                                             # x -> the Categorical key of its chosen bin
    for (col, lo, hi), x in zip(rules, combo):
        for key in cats[x].cat.categories:
            if isinstance(key, pd.Interval):
                if abs(float(key.left) - lo) < 1e-6 and abs(float(key.right) - hi) < 1e-6:
                    chosen[x] = key
            elif lo == hi and key == lo:
                chosen[x] = key

    x_labels = [config.CAP_X.get(x, x) for x in config.CAP_X]  # same column order as summary()
    rows, index = [], []
    for varied in combo:                                   # slide this X, hold the others fixed
        hold = pd.Series(True, index=sub.index)
        for x in combo:
            if x != varied:
                hold &= (cats[x] == chosen[x])
        for key in cats[varied].cat.categories:
            mask = hold & (cats[varied] == key)
            n = int(mask.sum())
            if n == 0:
                continue
            row = {lab: np.nan for lab in x_labels}        # X not in the combo stay NaN (like step 2)
            for x in combo:                                # held X show their chosen range
                row[config.CAP_X.get(x, x)] = _fmt(chosen[x])
            row[config.CAP_X.get(varied, varied)] = _fmt(key)   # slid X shows this bin
            row.update(_stats2(sub.loc[mask]))
            rows.append(row)
            tag = " < chosen" if key == chosen.get(varied) else ("  small-n" if n < min_n else "")
            index.append(f"{config.CAP_X.get(varied, varied)}{tag}")

    out = pd.DataFrame(rows, index=index)
    cols = x_labels + ["n", "cp_kappa", "cp_visc", "cpk_kappa", "cpk_visc", "cp_min", "cpk_min"]
    out = out[cols]
    for c in ("cp_kappa", "cp_visc", "cpk_kappa", "cpk_visc", "cp_min", "cpk_min"):
        out[c] = out[c].round(2)
    for c in x_labels:                                       # X not in the combo -> show "-" not NaN
        out[c] = out[c].astype(object).where(out[c].notna(), "-")
    chosen_combo = " x ".join(config.CAP_X.get(x, x) for x in combo)
    print(f"sensitivity around rank {rank}: {chosen_combo}  (hold 3, slide 1; index marks the slid X)")
    return out


# ---------------------------------------------------------------- timeline
def timeline(df=None, res=None, rank=0, gap_days=None, time_col="discharge_start"):
    """
    When did one box actually run? Takes the box at `rank` from search() (default best), finds every
    batch inside it, sorts by `time_col`, and splits them into BURSTS: a gap larger than `gap_days`
    (config.CAP_BURST_GAP_DAYS) starts a new burst. One row per burst with its date span, N and
    cp/cpk, plus an ALL row. Many spread-out bursts = the X window repeats; one tight burst = the
    result may be a calendar artifact (time confounder), not an X effect.
    """
    df = golden.load_golden() if df is None else df
    gap_days = config.CAP_BURST_GAP_DAYS if gap_days is None else gap_days
    if res is None:
        res = search(df)
    if res.empty:
        return res

    rules = res.iloc[rank]["rules"]                         # [(col, lo, hi), ...] of the chosen box
    sub = df.dropna(subset=[c for c, _, _ in rules] +
                    [config.CAP_TARGET, config.CAP_TARGET2, time_col]).copy()
    inside = pd.Series(True, index=sub.index)
    for col, lo, hi in rules:
        inside &= sub[col].between(lo, hi)
    box = sub.loc[inside].copy()
    box[time_col] = pd.to_datetime(box[time_col])
    box = box.sort_values(time_col)

    t = box[time_col]
    new_burst = t.diff() > pd.Timedelta(days=gap_days)      # gap too big -> next burst
    burst_id = new_burst.cumsum()

    rows = []
    for bid, idx in box.groupby(burst_id).groups.items():
        g = box.loc[idx]
        tg = g[time_col]
        s = _stats2(g)
        rows.append({
            "burst": int(bid) + 1,
            "first": tg.min().date(),
            "last": tg.max().date(),
            "span_days": int((tg.max() - tg.min()).days),
            "n": s["n"],
            "cp_kappa": s["cp_kappa"], "cp_visc": s["cp_visc"],
            "cpk_kappa": s["cpk_kappa"], "cpk_visc": s["cpk_visc"],
            "cp_min": s["cp_min"], "cpk_min": s["cpk_min"],
        })
    s = _stats2(box)
    rows.append({
        "burst": "ALL",
        "first": t.min().date(), "last": t.max().date(),
        "span_days": int((t.max() - t.min()).days),
        "n": s["n"],
        "cp_kappa": s["cp_kappa"], "cp_visc": s["cp_visc"],
        "cpk_kappa": s["cpk_kappa"], "cpk_visc": s["cpk_visc"],
        "cp_min": s["cp_min"], "cpk_min": s["cpk_min"],
    })

    out = pd.DataFrame(rows).set_index("burst")
    for c in ("cp_kappa", "cp_visc", "cpk_kappa", "cpk_visc", "cp_min", "cpk_min"):
        out[c] = out[c].round(2)

    n_bursts = int(burst_id.max()) + 1
    top_month = t.dt.to_period("M").value_counts()
    top_pct = int(round(100 * top_month.iloc[0] / len(t)))
    parts = []
    for c, lo, hi in rules:
        label = config.CAP_X.get(c, c)
        parts.append(f"{label} {lo}" if lo == hi else f"{label} {lo:.2f}-{hi:.2f}")
    print(f"timeline rank {rank}: {', '.join(parts)}")
    print(f"  {len(t)} batches in {n_bursts} burst(s) over {out.loc['ALL','span_days']} days; "
          f"busiest month {top_month.index[0]} = {top_pct}% of batches "
          f"(gap > {gap_days} d = new burst)")
    return out


# ---------------------------------------------------------------- by digester
def by_digester(df=None, top=1, combo_size=None, bins=None, min_n=None, dig_col="digester"):
    """
    Do the 4 digesters have different sweet spots? Runs search() separately inside each digester
    (digester dropped from the X, since it is fixed), and stacks the top `top` box of each into one
    table with a leading `digester` column and the same columns as summary(). N per digester is
    smaller, so min_n defaults lower (CAP_MIN_N // 2) than the pooled search.
    """
    df = golden.load_golden() if df is None else df
    combo_size = combo_size or config.CAP_COMBO_SIZE
    bins = bins or config.CAP_BINS
    min_n = min_n or max(5, config.CAP_MIN_N // 2)
    xs = [x for x in config.CAP_X if x != dig_col]          # fix the digester, search the rest

    frames = []
    for d in sorted(df[dig_col].dropna().unique()):
        sub = df[df[dig_col] == d]
        res_d = search(sub, combo_size, bins, min_n, xs=xs)
        if res_d.empty:
            print(f"  digester {int(d)}: no box with N >= {min_n}")
            continue
        s = summary(res_d, top)
        s.insert(0, "digester", int(d))
        frames.append(s)

    if not frames:
        print("no digester produced a box; lower min_n or combo_size.")
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    metrics = ["n", "cp_kappa", "cp_visc", "cpk_kappa", "cpk_visc", "cp_min", "cpk_min"]
    x_cols = [config.CAP_X[k] for k in config.CAP_X if config.CAP_X[k] in out.columns]
    out = out[["digester", "combo"] + x_cols + metrics]     # keep X in CAP_X order after concat
    print(f"by_digester: top {top} box per digester  "
          f"(digester dropped from X, combo size {combo_size}, {bins} bins/X, min N {min_n})")
    return out
