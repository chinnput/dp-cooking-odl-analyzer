#!/usr/bin/env python3
"""Data audit + distribution + capability + control chart for one quality variable.

Usage:
  python profile_data.py --file data.csv --y SCT --lsl 2.5 --usl 3.5 \
      [--target 3.0] [--time timestamp] [--group grade] [--outdir out]

Outputs (in outdir): audit.md, capability.md, hist_<y>.png, control_<y>.png
Works with .csv or .xlsx.
"""
import argparse, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats


def load(path):
    return pd.read_excel(path) if path.lower().endswith((".xlsx", ".xls")) else pd.read_csv(path)


def audit(df, time_col):
    lines = ["# Data audit", "", f"Rows: {len(df)}  Columns: {df.shape[1]}"]
    if time_col and time_col in df:
        t = pd.to_datetime(df[time_col], errors="coerce")
        lines.append(f"Time span: {t.min()} → {t.max()}")
        dt = t.sort_values().diff().dropna()
        if len(dt):
            lines.append(f"Median sampling interval: {dt.median()}  (max gap {dt.max()})")
    lines += ["", "| column | dtype | missing % | unique | std | flag |", "|---|---|---|---|---|---|"]
    for c in df.columns:
        s = df[c]
        miss = s.isna().mean() * 100
        uniq = s.nunique()
        std = s.std() if pd.api.types.is_numeric_dtype(s) else np.nan
        flag = []
        if miss > 20: flag.append("high missing")
        if uniq <= 1: flag.append("constant")
        elif pd.api.types.is_numeric_dtype(s) and uniq < 5: flag.append("few values")
        if pd.api.types.is_numeric_dtype(s) and len(s.dropna()) > 20:
            # flatline: longest run of identical consecutive values
            v = s.dropna().values
            runs = np.diff(np.flatnonzero(np.diff(np.r_[np.nan, v, np.nan]) != 0))
            if len(runs) and runs.max() > max(20, 0.05 * len(v)): flag.append(f"flatline run {runs.max()}")
        lines.append(f"| {c} | {s.dtype} | {miss:.1f} | {uniq} | {std:.4g} | {', '.join(flag)} |")
    return "\n".join(lines)


def capability(y, lsl, usl, target):
    y = y.dropna().values
    n = len(y)
    mu, s_all = y.mean(), y.std(ddof=1)
    mr = np.abs(np.diff(y))
    s_within = mr.mean() / 1.128 if len(mr) else s_all
    out = {"n": n, "mean": mu, "median": np.median(y), "std_overall": s_all, "std_within": s_within,
           "skew": stats.skew(y), "kurtosis": stats.kurtosis(y)}
    def idx(s):
        r = {}
        if lsl is not None and usl is not None: r["Cp"] = (usl - lsl) / (6 * s)
        cands = []
        if usl is not None: cands.append((usl - mu) / (3 * s))
        if lsl is not None: cands.append((mu - lsl) / (3 * s))
        if cands: r["Cpk"] = min(cands)
        return r
    w, o = idx(s_within), idx(s_all)
    for k, v in w.items(): out[k] = v
    for k, v in o.items(): out[k.replace("C", "P", 1)] = v
    if "Cpk" in out and n > 1:  # approx 95% CI (Bissell)
        se = np.sqrt(1 / (9 * n) + out["Cpk"] ** 2 / (2 * (n - 1)))
        out["Cpk_95CI"] = (out["Cpk"] - 1.96 * se, out["Cpk"] + 1.96 * se)
    oos = np.zeros(n, bool)
    if lsl is not None: oos |= y < lsl
    if usl is not None: oos |= y > usl
    out["pct_out_of_spec_actual"] = oos.mean() * 100
    pred = 0.0
    if lsl is not None: pred += stats.norm.cdf(lsl, mu, s_all)
    if usl is not None: pred += stats.norm.sf(usl, mu, s_all)
    out["pct_out_of_spec_normal_pred"] = pred * 100
    for k, exp in [(1, 31.73), (2, 4.55), (3, 0.27)]:
        out[f"pct_beyond_{k}sigma"] = (np.abs(y - mu) > k * s_all).mean() * 100
        out[f"expected_beyond_{k}sigma"] = exp
    if target is not None:
        out["offset_from_target_in_sigma"] = (mu - target) / s_all
    samp = y if n <= 5000 else np.random.default_rng(0).choice(y, 5000, replace=False)
    out["shapiro_p"] = stats.shapiro(samp).pvalue if n >= 3 else np.nan
    return out


def we_rules(y, center, sigma):
    """Return indices violating Western Electric rules 1,2,4 (subset)."""
    z = (y - center) / sigma
    v = {"rule1_beyond_3s": np.flatnonzero(np.abs(z) > 3)}
    r2 = []
    for i in range(2, len(z)):
        w = z[i - 2:i + 1]
        if (w > 2).sum() >= 2 or (w < -2).sum() >= 2: r2.append(i)
    v["rule2_2of3_beyond_2s"] = np.array(r2)
    r4 = []
    for i in range(7, len(z)):
        w = z[i - 7:i + 1]
        if (w > 0).all() or (w < 0).all(): r4.append(i)
    v["rule4_8_same_side"] = np.array(r4)
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True); ap.add_argument("--y", required=True)
    ap.add_argument("--lsl", type=float); ap.add_argument("--usl", type=float)
    ap.add_argument("--target", type=float); ap.add_argument("--time")
    ap.add_argument("--group", help="e.g. grade; capability reported per group too")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--query", help='pandas filter, e.g. "grade == \'KA125\' and speed > 500"')
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    df = load(a.file)
    if a.query: df = df.query(a.query)
    if a.time and a.time in df:
        df[a.time] = pd.to_datetime(df[a.time], errors="coerce"); df = df.sort_values(a.time)
    open(os.path.join(a.outdir, "audit.md"), "w").write(audit(df, a.time))

    y = pd.to_numeric(df[a.y], errors="coerce")
    cap = capability(y, a.lsl, a.usl, a.target)
    lines = [f"# Capability: {a.y}", "", "| metric | value |", "|---|---|"]
    for k, v in cap.items():
        lines.append(f"| {k} | {v if isinstance(v, tuple) else round(float(v), 4)} |")
    if a.group and a.group in df:
        lines += ["", f"## By {a.group}", "", "| group | n | mean | std | Cpk | Ppk | % OOS |", "|---|---|---|---|---|---|---|"]
        for g, sub in df.groupby(a.group):
            c = capability(pd.to_numeric(sub[a.y], errors="coerce"), a.lsl, a.usl, a.target)
            lines.append(f"| {g} | {c['n']} | {c['mean']:.4g} | {c['std_overall']:.4g} | "
                         f"{c.get('Cpk', np.nan):.3f} | {c.get('Ppk', np.nan):.3f} | {c['pct_out_of_spec_actual']:.2f} |")
    yv = y.dropna().values
    viol = we_rules(yv, cap["mean"], cap["std_within"])
    lines += ["", "## Control-chart rule violations (limits from whole data; prefer a stable reference period)"]
    for k, idx in viol.items(): lines.append(f"- {k}: {len(idx)} points")
    open(os.path.join(a.outdir, "capability.md"), "w").write("\n".join(lines))

    # Histogram
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(yv, bins="fd", density=True, alpha=0.6, color="#4C72B0")
    xs = np.linspace(yv.min(), yv.max(), 300)
    ax.plot(xs, stats.gaussian_kde(yv)(xs), "k-", lw=1, label="KDE")
    ax.plot(xs, stats.norm.pdf(xs, cap["mean"], cap["std_overall"]), "--", color="gray", label="Normal fit")
    for val, lab, col in [(a.lsl, "LSL", "red"), (a.usl, "USL", "red"), (a.target, "Target", "green")]:
        if val is not None: ax.axvline(val, color=col, ls="-", lw=1.5, label=lab)
    for k in (2, 3):
        for sgn in (-1, 1):
            ax.axvline(cap["mean"] + sgn * k * cap["std_overall"], color="orange", ls=":", lw=1)
    ax.set_title(f"{a.y}  Cpk={cap.get('Cpk', float('nan')):.2f}  Ppk={cap.get('Ppk', float('nan')):.2f}  "
                 f"OOS={cap['pct_out_of_spec_actual']:.1f}%  (orange: ±2σ/±3σ)")
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(a.outdir, f"hist_{a.y}.png"), dpi=120)

    # I-MR chart
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    xax = df.loc[y.notna(), a.time].values if a.time and a.time in df else np.arange(len(yv))
    c, s = cap["mean"], cap["std_within"]
    a1.plot(xax, yv, lw=0.7, marker=".", ms=2)
    for k, st in [(3, "-"), (2, "--")]:
        a1.axhline(c + k * s, color="red", ls=st, lw=0.8); a1.axhline(c - k * s, color="red", ls=st, lw=0.8)
    a1.axhline(c, color="green", lw=0.8)
    bad = viol["rule1_beyond_3s"]
    a1.plot(np.asarray(xax)[bad], yv[bad], "ro", ms=4)
    for val in (a.lsl, a.usl):
        if val is not None: a1.axhline(val, color="purple", lw=1.2)
    a1.set_title(f"I chart {a.y} (red: ±2σ/3σ within; purple: spec)")
    mr = np.abs(np.diff(yv)); a2.plot(np.asarray(xax)[1:], mr, lw=0.7)
    a2.axhline(mr.mean(), color="green", lw=0.8); a2.axhline(3.267 * mr.mean(), color="red", lw=0.8)
    a2.set_title("Moving range"); fig.tight_layout()
    fig.savefig(os.path.join(a.outdir, f"control_{a.y}.png"), dpi=120)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
