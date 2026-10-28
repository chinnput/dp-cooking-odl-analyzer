"""
Golden window: which X range makes a batch fail QC, with statistical evidence.

Every outcome is a FAIL event (1 = failed), so "bad side" always means the side of a
threshold with the higher fail rate:
  fail        any Y outside config.GOLDEN_SPEC (= Non-Golden)
  kappa_high  Kappa above spec        visc_high  Viscosity above spec
  visc_low    Viscosity below spec

Evidence steps for one X and one outcome:
  1. curve        fail rate per quantile bin of X, with Wilson 95% CI
  2. threshold    best cut (max chi-square), fail rate on each side, risk ratio, Fisher p
                  p_perm: permutation p that accounts for searching the cut, with the
                  outcome shuffled INSIDE each month (so the season cannot create the effect)
                  cut_p5 / cut_p95: week-block bootstrap range of the cut
  3. adjusted     Mantel-Haenszel risk ratio / risk difference stratified by month,
                  + how many months show the same direction
  4. future       cut found on the first (1 - TEST_SHARE) of the time, checked on the rest
  5. FDR          Benjamini-Hochberg q over all X of one outcome
  6. gain         share of batches on the bad side, and fail rate if they moved (MH-adjusted)

Grade:  A = 5 + 3 + 4 + months all agree     B = 5 + (3 or 4)     C = 5 only     - = not significant
Pure logic, no plotting. Data: batch_master via data.py, filters from config.
"""
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, norm

import config
import data

OUTCOMES = {
    "fail": "Fail QC (any)",
    "kappa_high": "Kappa high",
    "visc_high": "Viscosity high",
    "visc_low": "Viscosity low",
}


# ---------------------------------------------------------------- data
def golden_features(df=None):
    """FEATURES + GOLDEN_EXTRA that exist as columns (dict column -> label)."""
    feats = {**config.FEATURES, **config.GOLDEN_EXTRA}
    if df is not None:
        feats = {c: l for c, l in feats.items() if c in df.columns and df[c].notna().sum() > 0}
    return feats


def load_golden():
    """Batches with both lab results, the golden flag, every fail mode, month and week."""
    m = data.add_derived(data.load_master())
    if config.QUALITY_FLAG_OK and "quality_flag" in m:
        m = m[m["quality_flag"] == "ok"]
    ys = list(config.GOLDEN_SPEC)
    m = m.dropna(subset=ys)
    lo, hi = config.TARGET_RANGE                        # Viscosity spike filter
    m = m[m["press1_viscosity"].between(lo, hi)]
    if config.GOLDEN_DATE_FROM:
        m = m[m["batch_start"] >= config.GOLDEN_DATE_FROM]
    if config.GOLDEN_DATE_TO:
        m = m[m["batch_start"] < config.GOLDEN_DATE_TO]

    (k_lo, k_hi), (v_lo, v_hi) = config.GOLDEN_SPEC["press1_kappa"], config.GOLDEN_SPEC["press1_viscosity"]
    m = m.copy()
    m["kappa_high"] = (m["press1_kappa"] > k_hi).astype(int)
    m["kappa_low"] = (m["press1_kappa"] < k_lo).astype(int)
    m["visc_high"] = (m["press1_viscosity"] > v_hi).astype(int)
    m["visc_low"] = (m["press1_viscosity"] < v_lo).astype(int)
    m["fail"] = m[["kappa_high", "kappa_low", "visc_high", "visc_low"]].max(axis=1)
    m["golden"] = 1 - m["fail"]
    m["month"] = m["batch_start"].dt.to_period("M").astype(str)
    m["week"] = m["batch_start"].dt.to_period("W").astype(str)
    m = m.sort_values("batch_start").reset_index(drop=True)
    print(f"golden data: {len(m)} batches with Kappa + Viscosity "
          f"({m['batch_start'].min():%Y-%m-%d} .. {m['batch_start'].max():%Y-%m-%d}), "
          f"golden {m['golden'].sum()} ({m['golden'].mean():.0%})")
    return m


def fail_modes(df):
    """Why batches fail: counts and share of each fail mode, overall and per month."""
    cols = ["fail", "kappa_high", "kappa_low", "visc_high", "visc_low"]
    overall = df[cols].agg(["sum", "mean"]).T.rename(columns={"sum": "batches", "mean": "share"})
    by_month = df.groupby("month")[cols].mean().round(2)
    by_month.insert(0, "n", df.groupby("month").size())
    return overall.round(3), by_month


# ---------------------------------------------------------------- outliers
def outlier_mask(df, x, method=None):
    """True where X is an outlier by `method` ("2sd" / "iqr3"; None -> no outliers), per digester if set."""
    method = config.GOLDEN_OUTLIER if method is None else method
    out = pd.Series(False, index=df.index)
    if not method:
        return out
    groups = df.groupby("digester") if config.GOLDEN_OUTLIER_BY_DIGESTER else [(None, df)]
    for _, g in groups:
        v = g[x]
        if method == "2sd":
            bad = (v - v.mean()).abs() > 2 * v.std()
        elif method == "iqr3":
            q1, q3 = v.quantile([0.25, 0.75])
            bad = (v < q1 - 3 * (q3 - q1)) | (v > q3 + 3 * (q3 - q1))
        else:
            raise ValueError(f"unknown outlier method '{method}'")
        out.loc[g.index] = bad.fillna(False)
    return out


def clean_x(df, x, method=None):
    """Copy of df with the outliers of ONE column set to NaN (other columns untouched)."""
    mask = outlier_mask(df, x, method)
    if not mask.any():
        return df
    df = df.copy()
    df.loc[mask, x] = np.nan
    return df


def outlier_report(df, features=None):
    """How many values each method would remove, per X (per digester when configured)."""
    feats = features or golden_features(df)
    rows = []
    for x, lab in feats.items():
        v = df[x]
        rows.append({"X": lab, "n": int(v.notna().sum()), "skew": round(v.skew(), 1),
                     "min": v.min(), "median": v.median(), "max": v.max(),
                     "removed_2sd": int(outlier_mask(df, x, "2sd").sum()),
                     "removed_iqr3": int(outlier_mask(df, x, "iqr3").sum())})
    return pd.DataFrame(rows).set_index("X").round(3)


# ---------------------------------------------------------------- helpers
def wilson(k, n, z=1.96):
    """Wilson 95% CI for a proportion k/n (works for small n and 0 / n)."""
    k, n = np.asarray(k, float), np.asarray(n, float)
    p = np.where(n > 0, k / np.maximum(n, 1), np.nan)
    den = 1 + z ** 2 / n
    mid = (p + z ** 2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return mid - half, mid + half


def _xy(df, x, event):
    sub = df[[x, event, "month", "week", "batch_start"]].dropna(subset=[x])
    return sub.reset_index(drop=True)


def _cuts(xv):
    """Candidate cuts = quantiles that keep >= GOLDEN_MIN_SIDE (and >= 20 batches) on each side."""
    n = len(xv)
    qs = np.unique(np.quantile(xv, np.arange(0.10, 0.91, 0.025)))
    keep = []
    for c in qs:
        n_hi = (xv > c).sum()
        side_min = max(20, config.GOLDEN_MIN_SIDE * n)
        if min(n_hi, n - n_hi) >= side_min:
            keep.append(c)
    return np.array(keep)


def _chi2(xv, ev, cuts):
    """Chi-square of the 2x2 table (x > cut vs fail) for every cut. Returns chi2, fail rate above, below."""
    above = xv[None, :] > cuts[:, None]                 # cuts x n
    n1 = above.sum(1)
    n0 = len(xv) - n1
    a = (above * ev[None, :]).sum(1)                    # fails above
    c = ev.sum() - a                                    # fails below
    k = ev.sum()
    n = len(xv)
    den = n1 * n0 * k * (n - k)
    chi = np.where(den > 0, n * (a * (n0 - c) - c * (n1 - a)) ** 2 / np.maximum(den, 1), 0.0)
    return chi, a / np.maximum(n1, 1), c / np.maximum(n0, 1)


# ---------------------------------------------------------------- step 1
def curve(df, x, event="fail", q=5):
    """Fail rate per quantile bin of X with Wilson CI (outliers of X removed per config)."""
    sub = _xy(clean_x(df, x), x, event)
    bins = pd.qcut(sub[x], q, duplicates="drop")
    t = sub.groupby(bins, observed=True).agg(n=(event, "size"), fails=(event, "sum"),
                                             x_lo=(x, "min"), x_hi=(x, "max"))
    t["fail_rate"] = t["fails"] / t["n"]
    t["ci_lo"], t["ci_hi"] = wilson(t["fails"], t["n"])
    return t


# ---------------------------------------------------------------- step 2
def threshold(df, x, event="fail"):
    """Best cut, the bad side and its risk vs the good side."""
    sub = _xy(df, x, event)
    xv, ev = sub[x].to_numpy(float), sub[event].to_numpy(int)
    cuts = _cuts(xv)
    if len(cuts) == 0 or ev.sum() == 0 or ev.sum() == len(ev):
        return None
    chi, r_hi, r_lo = _chi2(xv, ev, cuts)
    i = int(np.argmax(chi))
    cut = cuts[i]
    bad_high = r_hi[i] > r_lo[i]
    bad = xv > cut if bad_high else xv <= cut
    a, n1 = ev[bad].sum(), bad.sum()
    c, n0 = ev[~bad].sum(), (~bad).sum()
    rr = (a / n1) / (c / n0) if c > 0 else np.inf
    se = np.sqrt(1 / max(a, 0.5) - 1 / n1 + 1 / max(c, 0.5) - 1 / n0)
    lo1, hi1 = wilson(a, n1)
    lo0, hi0 = wilson(c, n0)
    return {
        "x": x, "event": event, "n": len(xv), "cut": cut, "bad_side": ">" if bad_high else "<=",
        "n_bad": int(n1), "fail_bad": a / n1, "fail_bad_ci": (float(lo1), float(hi1)),
        "n_good": int(n0), "fail_good": c / n0, "fail_good_ci": (float(lo0), float(hi0)),
        "rr": rr, "rr_ci": (rr * np.exp(-1.96 * se), rr * np.exp(1.96 * se)),
        "fisher_p": fisher_exact([[a, n1 - a], [c, n0 - c]])[1],
        "chi2": chi[i], "_cuts": cuts, "_sub": sub,
    }


def perm_p(t, n_perm=None, seed=0):
    """Permutation p for the best cut: shuffle fails inside each month, redo the cut search."""
    n_perm = n_perm or config.GOLDEN_N_PERM
    sub, cuts = t["_sub"], t["_cuts"]
    xv, ev = sub[t["x"]].to_numpy(float), sub[t["event"]].to_numpy(int)
    groups = [np.flatnonzero(sub["month"].to_numpy() == mo) for mo in sub["month"].unique()]
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_perm):
        e = ev.copy()
        for g in groups:
            e[g] = rng.permutation(e[g])
        if _chi2(xv, e, cuts)[0].max() >= t["chi2"]:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def boot_cut(t, n_boot=None, seed=0):
    """Week-block bootstrap of the cut: P5 / P95 and how often the bad side is the same."""
    n_boot = n_boot or config.GOLDEN_N_BOOT
    sub = t["_sub"]
    weeks = sub["week"].unique()
    idx = {w: np.flatnonzero(sub["week"].to_numpy() == w) for w in weeks}
    rng = np.random.default_rng(seed)
    cuts, same = [], 0
    for _ in range(n_boot):
        pick = np.concatenate([idx[w] for w in rng.choice(weeks, len(weeks))])
        b = threshold(sub.iloc[pick].reset_index(drop=True), t["x"], t["event"])
        if b is None:
            continue
        cuts.append(b["cut"])
        same += b["bad_side"] == t["bad_side"]
    cuts = np.array(cuts)
    return np.quantile(cuts, 0.05), np.quantile(cuts, 0.95), same / max(len(cuts), 1)


# ---------------------------------------------------------------- step 3
def month_adjusted(t):
    """Mantel-Haenszel RR and RD stratified by month, + months with the same direction."""
    sub = t["_sub"]
    bad = (sub[t["x"]] > t["cut"]) if t["bad_side"] == ">" else (sub[t["x"]] <= t["cut"])
    num_rr = den_rr = var_num = 0.0
    rd_num = rd_den = rd_var = 0.0
    months = []
    for mo, g in sub.groupby("month"):
        b = bad.loc[g.index]
        n1, n0 = b.sum(), (~b).sum()
        if n1 == 0 or n0 == 0:
            continue
        a, c = g.loc[b, t["event"]].sum(), g.loc[~b, t["event"]].sum()
        n = n1 + n0
        num_rr += a * n0 / n
        den_rr += c * n1 / n
        var_num += (n1 * n0 * (a + c) - a * c * n) / n ** 2
        w = n1 * n0 / n
        p1, p0 = a / n1, c / n0
        rd_num += w * (p1 - p0)
        rd_den += w
        rd_var += w ** 2 * (p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
        if min(n1, n0) >= 5:
            months.append({"month": mo, "n_bad": int(n1), "fail_bad": p1, "n_good": int(n0), "fail_good": p0})
    rr = num_rr / den_rr if den_rr > 0 else np.nan
    se = np.sqrt(var_num / (num_rr * den_rr)) if num_rr > 0 and den_rr > 0 else np.nan
    rd = rd_num / rd_den if rd_den > 0 else np.nan
    rd_se = np.sqrt(rd_var) / rd_den if rd_den > 0 else np.nan
    per_month = pd.DataFrame(months)
    agree = int((per_month["fail_bad"] > per_month["fail_good"]).sum()) if len(per_month) else 0
    return {
        "mh_rr": rr, "mh_rr_ci": (rr * np.exp(-1.96 * se), rr * np.exp(1.96 * se)),
        "mh_p": 2 * norm.sf(abs(np.log(rr) / se)) if se and np.isfinite(se) and rr > 0 else np.nan,
        "mh_rd": rd, "mh_rd_ci": (rd - 1.96 * rd_se, rd + 1.96 * rd_se),
        "months_agree": agree, "months_tested": len(per_month), "per_month": per_month,
    }


# ---------------------------------------------------------------- step 4
def future_check(df, x, event="fail"):
    """Cut from the first part of the time, fail rates of each side in the later part."""
    sub = _xy(df, x, event)
    split = int(len(sub) * (1 - config.TEST_SHARE))
    train, test = sub.iloc[:split], sub.iloc[split:]
    t = threshold(train.reset_index(drop=True), x, event)
    if t is None:
        return None
    bad = (test[x] > t["cut"]) if t["bad_side"] == ">" else (test[x] <= t["cut"])
    n1, n0 = bad.sum(), (~bad).sum()
    if n1 == 0 or n0 == 0:
        return {"test_from": test["batch_start"].min(), "train_cut": t["cut"], "test_n_bad": int(n1),
                "test_fail_bad": np.nan, "test_fail_good": np.nan, "test_p": np.nan}
    a, c = test.loc[bad, event].sum(), test.loc[~bad, event].sum()
    return {"test_from": test["batch_start"].min(), "train_cut": t["cut"], "train_side": t["bad_side"],
            "test_n_bad": int(n1), "test_fail_bad": a / n1, "test_n_good": int(n0), "test_fail_good": c / n0,
            "test_p": fisher_exact([[a, n1 - a], [c, n0 - c]], alternative="greater")[1]}


# ---------------------------------------------------------------- step 5
def bh(p):
    """Benjamini-Hochberg q-values."""
    p = np.asarray(p, float)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    pv = p[ok]
    order = np.argsort(pv)
    ranked = pv[order] * len(pv) / (np.arange(len(pv)) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(pv)
    out[order] = np.minimum(ranked, 1)
    q[ok] = out
    return q


def _grade(r):
    sig = r["q"] < config.GOLDEN_FDR
    adj = r["mh_p"] < 0.05 and r["mh_rr"] > 1
    fut = r["test_fail_bad"] > r["test_fail_good"] and r["test_p"] < 0.10
    months = r["months_tested"] > 0 and r["months_agree"] == r["months_tested"]
    if sig and adj and fut and months:
        return "A"
    if sig and (adj or fut):
        return "B"
    if sig:
        return "C"
    return "-"


# ---------------------------------------------------------------- steps 1-6 for every X
def screen(df, event="fail", features=None, progress=True):
    """Evidence table for every X for one fail outcome, best evidence first."""
    feats = features or golden_features(df)
    base_fail = df[event].mean()
    rows, details = [], {}
    for x, lab in feats.items():
        dfx = clean_x(df, x)                     # outliers of this X only (config.GOLDEN_OUTLIER)
        t = threshold(dfx, x, event)
        if t is None:
            continue
        if progress:
            print(f"  {OUTCOMES.get(event, event):14s} {lab}")
        adj = month_adjusted(t)
        fut = future_check(dfx, x, event) or {}
        b_lo, b_hi, b_same = boot_cut(t)
        share_bad = t["n_bad"] / t["n"]
        rows.append({
            "x": x, "label": lab, "n": t["n"],
            "bad_side": f"{t['bad_side']} {t['cut']:.4g}",
            "cut": t["cut"], "side": t["bad_side"],
            "cut_p5": b_lo, "cut_p95": b_hi, "side_stable": b_same,
            "n_bad": t["n_bad"], "fail_bad": t["fail_bad"], "fail_good": t["fail_good"],
            "rr": t["rr"], "rr_lo": t["rr_ci"][0], "rr_hi": t["rr_ci"][1],
            "fisher_p": t["fisher_p"], "p_perm": perm_p(t),
            "mh_rr": adj["mh_rr"], "mh_rr_lo": adj["mh_rr_ci"][0], "mh_rr_hi": adj["mh_rr_ci"][1],
            "mh_p": adj["mh_p"], "mh_rd": adj["mh_rd"],
            "months_agree": adj["months_agree"], "months_tested": adj["months_tested"],
            "test_from": fut.get("test_from"), "test_fail_bad": fut.get("test_fail_bad", np.nan),
            "test_fail_good": fut.get("test_fail_good", np.nan), "test_p": fut.get("test_p", np.nan),
            "share_bad": share_bad,
            "fail_now": base_fail,
            "fail_if_moved": base_fail - share_bad * max(adj["mh_rd"], 0) if np.isfinite(adj["mh_rd"]) else np.nan,
        })
        details[x] = {"threshold": t, "adjusted": adj}
    res = pd.DataFrame(rows)
    if res.empty:
        return res, details
    res["q"] = bh(res["p_perm"])
    res["grade"] = res.apply(_grade, axis=1)
    order = {"A": 0, "B": 1, "C": 2, "-": 3}
    res = res.sort_values(["grade", "p_perm"], key=lambda s: s.map(order) if s.name == "grade" else s)
    return res.reset_index(drop=True), details


def summary(res):
    """Short, readable view of a screen() table."""
    if res.empty:
        return res
    out = pd.DataFrame({
        "X": res["label"],
        "Grade": res["grade"],
        "Bad side": res["bad_side"],
        "Cut 90% range": [f"{a:.4g} - {b:.4g}" for a, b in zip(res["cut_p5"], res["cut_p95"])],
        "Fail % at bad side": [f"{a:.0%} ({sd} {c:.4g})" for a, sd, c in zip(res["fail_bad"], res["side"], res["cut"])],
        "Fail % at good side": [f"{b:.0%} ({'>' if sd == '<=' else '<='} {c:.4g})"
                                for b, sd, c in zip(res["fail_good"], res["side"], res["cut"])],
        "RR [95% CI]": [f"{r:.2f} [{lo:.2f}-{hi:.2f}]" for r, lo, hi in zip(res["rr"], res["rr_lo"], res["rr_hi"])],
        "p perm (q)": [f"{p:.3f} ({q:.3f})" for p, q in zip(res["p_perm"], res["q"])],
        "MH RR by month": [f"{r:.2f} (p {p:.3f})" for r, p in zip(res["mh_rr"], res["mh_p"])],
        "Months agree": [f"{a}/{b}" for a, b in zip(res["months_agree"], res["months_tested"])],
        "Future fail % at bad side": [f"{a:.0%}" if np.isfinite(a) else "-" for a in res["test_fail_bad"]],
        "Future fail % at good side": [f"{b:.0%}" if np.isfinite(b) else "-" for b in res["test_fail_good"]],
        "Future p": [f"{p:.2f}" if np.isfinite(p) else "-" for p in res["test_p"]],
        "On bad side now": [f"{s:.0%}" for s in res["share_bad"]],
        "Fail now -> if moved": [f"{a:.0%} -> {b:.0%}" for a, b in zip(res["fail_now"], res["fail_if_moved"])],
    })
    return out


# ---------------------------------------------------------------- step 6: window
def window(results, df=None, grades=("A", "B")):
    """
    Operating window per X from the fail-mode screens: a bad side '<= cut' gives a lower limit,
    a bad side '> cut' gives an upper limit. results = {event: screen table}.
    data_p5 / data_p95: the range the plant has really run. A side with no evidence should stay
    inside it - the data cannot say what happens beyond (e.g. over-cooking).
    """
    rows = {}
    for event, res in results.items():
        for r in res[res["grade"].isin(grades)].itertuples():
            w = rows.setdefault(r.x, {"X": r.label, "keep_above": np.nan, "lower_from": "",
                                      "keep_at_or_below": np.nan, "upper_from": ""})
            reason = f"{OUTCOMES[event]} ({r.grade})"
            if r.side == "<=":          # too low is bad -> keep X above the cut
                if np.isnan(w["keep_above"]) or r.cut > w["keep_above"]:
                    w["keep_above"], w["lower_from"] = r.cut, reason
            else:                       # too high is bad -> keep X at or below the cut
                if np.isnan(w["keep_at_or_below"]) or r.cut < w["keep_at_or_below"]:
                    w["keep_at_or_below"], w["upper_from"] = r.cut, reason
    out = pd.DataFrame(rows.values(), index=list(rows.keys()))
    if out.empty:
        return out
    out["conflict"] = out["keep_above"] > out["keep_at_or_below"]
    if df is not None:
        out["data_p5"] = [df[x].quantile(0.05) for x in out.index]
        out["data_p95"] = [df[x].quantile(0.95) for x in out.index]
    return out


def window_check(df, rules, event="fail"):
    """
    Test a combined window. rules = [(column, ">", value), (column, "<=", value), ...] = conditions
    a batch must meet to be INSIDE. Returns fail rate inside vs outside (Wilson CI), Fisher p,
    Mantel-Haenszel RR by month and the per-month table.
    """
    for col, _, _ in rules:
        df = clean_x(df, col)
    sub = df.dropna(subset=[c for c, _, _ in rules]).copy()
    inside = pd.Series(True, index=sub.index)
    for col, op, val in rules:
        inside &= (sub[col] > val) if op == ">" else (sub[col] <= val)
    # reuse the threshold machinery: outside = bad side
    sub["_outside"] = (~inside).astype(int)
    t = {"x": "_outside", "event": event, "cut": 0.5, "bad_side": ">",
         "_sub": sub[["_outside", event, "month", "week", "batch_start"]].reset_index(drop=True)}
    adj = month_adjusted(t)
    a, n1 = sub.loc[~inside, event].sum(), (~inside).sum()
    c, n0 = sub.loc[inside, event].sum(), inside.sum()
    lo_in, hi_in = wilson(c, n0)
    lo_out, hi_out = wilson(a, n1)
    summary_row = {
        "n": len(sub), "n_inside": int(n0), "share_inside": n0 / len(sub),
        "fail_inside": c / n0 if n0 else np.nan, "fail_inside_ci": (float(lo_in), float(hi_in)),
        "fail_outside": a / n1 if n1 else np.nan, "fail_outside_ci": (float(lo_out), float(hi_out)),
        "fisher_p": fisher_exact([[a, n1 - a], [c, n0 - c]])[1] if n0 and n1 else np.nan,
        "mh_rr_outside": adj["mh_rr"], "mh_rr_ci": adj["mh_rr_ci"], "mh_p": adj["mh_p"],
        "months_agree": f"{adj['months_agree']}/{adj['months_tested']}",
    }
    return summary_row, adj["per_month"].rename(columns={"n_bad": "n_outside", "fail_bad": "fail_outside",
                                                         "n_good": "n_inside", "fail_good": "fail_inside"})


def sensitivity(df, x, event="fail", methods=(None, "2sd", "iqr3"), n_perm=500):
    """Same threshold test with no / 2-SD / 3-IQR outlier removal - does the conclusion hold?"""
    rows = []
    for m in methods:
        dfx = df if m is None else clean_x(df, x, m)
        t = threshold(dfx, x, event)
        if t is None:
            continue
        adj = month_adjusted(t)
        rows.append({"outliers": m or "keep all", "n": t["n"], "removed": len(df[x].dropna()) - t["n"],
                     "bad side": f"{t['bad_side']} {t['cut']:.4g}",
                     "fail bad / good": f"{t['fail_bad']:.0%} / {t['fail_good']:.0%}",
                     "RR": round(t["rr"], 2), "p perm": round(perm_p(t, n_perm), 3),
                     "MH RR": round(adj["mh_rr"], 2), "months agree": f"{adj['months_agree']}/{adj['months_tested']}"})
    return pd.DataFrame(rows).set_index("outliers")
