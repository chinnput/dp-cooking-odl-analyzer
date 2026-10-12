#!/usr/bin/env python3
"""Good-vs-bad comparison, threshold finding, golden operating window, and model importance.

Usage:
  python golden_window.py --file data.csv --y SCT --x speed refining starch ... \
      [--lsl 2.5 --usl 3.5 --target 3.0] [--good-quantile 0.25] [--controllable a b] [--outdir out]

"Good" = in spec AND |Y - target| in the best --good-quantile of rows (target defaults to spec midpoint
or median). "Bad" = out of spec (or worst quantile if nothing is out of spec).
Outputs: good_vs_bad.md, golden_window.md, importance.md, window_plot.png, pdp.png
"""
import argparse, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.inspection import permutation_importance, partial_dependence


def load(p):
    return pd.read_excel(p) if p.lower().endswith((".xlsx", ".xls")) else pd.read_csv(p)


def cliffs_delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if len(a) * len(b) > 4e6:
        rng = np.random.default_rng(0); a = rng.choice(a, 2000); b = rng.choice(b, 2000)
    gt = (a[:, None] > b[None, :]).mean(); lt = (a[:, None] < b[None, :]).mean()
    return gt - lt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True); ap.add_argument("--y", required=True)
    ap.add_argument("--x", nargs="+", required=True)
    ap.add_argument("--lsl", type=float); ap.add_argument("--usl", type=float); ap.add_argument("--target", type=float)
    ap.add_argument("--good-quantile", type=float, default=0.25)
    ap.add_argument("--controllable", nargs="*", help="subset of x that operators can set; window uses these")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--query", help='pandas filter, e.g. "grade == \'KA125\' and speed > 500"')
    a = ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
    d = load(a.file)
    if a.query: d = d.query(a.query)
    d = d.dropna(subset=a.x + [a.y]).reset_index(drop=True)
    y = d[a.y]
    tgt = a.target if a.target is not None else ((a.lsl + a.usl) / 2 if a.lsl is not None and a.usl is not None else y.median())
    inspec = pd.Series(True, index=d.index)
    if a.lsl is not None: inspec &= y >= a.lsl
    if a.usl is not None: inspec &= y <= a.usl
    dev = (y - tgt).abs()
    good = inspec & (dev <= dev.quantile(a.good_quantile))
    bad = ~inspec if (~inspec).sum() >= 10 else dev >= dev.quantile(1 - a.good_quantile)
    out = [f"# Good vs bad for {a.y}", f"target={tgt:.4g}; good n={good.sum()}; bad n={bad.sum()} "
           f"({'out of spec' if (~inspec).sum() >= 10 else 'worst deviation quantile'})", "",
           "| x | good median | bad median | diff | Cliff's δ | MW p | KS p |", "|---|---|---|---|---|---|---|"]
    rows = []
    for x in a.x:
        g, b = d.loc[good, x], d.loc[bad, x]
        cd = cliffs_delta(g, b); mw = stats.mannwhitneyu(g, b).pvalue; ks = stats.ks_2samp(g, b).pvalue
        rows.append((x, g.median(), b.median(), g.median() - b.median(), cd, mw, ks))
    rows.sort(key=lambda r: -abs(r[4]))
    for r in rows: out.append(f"| {r[0]} | {r[1]:.4g} | {r[2]:.4g} | {r[3]:.4g} | {r[4]:.3f} | {r[5]:.2g} | {r[6]:.2g} |")
    out.append("\n|δ| ≈ 0.15 small, 0.33 medium, 0.47 large")
    open(os.path.join(a.outdir, "good_vs_bad.md"), "w").write("\n".join(out))

    # thresholds: decile bins, % OOS and mean Y per bin
    thr = ["# Binned analysis (deciles of each X)", ""]
    for x in a.x:
        try:
            bins = pd.qcut(d[x], 10, duplicates="drop")
        except ValueError:
            continue
        t = d.assign(oos=~inspec).groupby(bins, observed=True).agg(n=(a.y, "size"), y_mean=(a.y, "mean"),
                                                                  y_std=(a.y, "std"), pct_oos=("oos", "mean"))
        t["pct_oos"] *= 100
        thr += [f"## {x}", t.round(4).to_markdown(), ""]
    open(os.path.join(a.outdir, "binned.md"), "w").write("\n".join(thr))

    # golden window from good runs (P10-P90), on controllable X
    wx = a.controllable or a.x
    win = {x: (d.loc[good, x].quantile(0.10), d.loc[good, x].quantile(0.90)) for x in wx}
    inside = pd.Series(True, index=d.index)
    for x, (lo, hi) in win.items(): inside &= d[x].between(lo, hi)
    def summ(m):
        s = y[m]
        return f"n={m.sum()} ({100*m.mean():.1f}% of data), mean={s.mean():.4g}, std={s.std():.4g}, %OOS={100*(~inspec[m]).mean():.2f}"
    gw = ["# Golden operating window (P10–P90 of good runs)", "", "| x | low | high | overall P10 | overall P90 |", "|---|---|---|---|---|"]
    for x, (lo, hi) in win.items():
        gw.append(f"| {x} | {lo:.4g} | {hi:.4g} | {d[x].quantile(.1):.4g} | {d[x].quantile(.9):.4g} |")
    gw += ["", f"All data: {summ(pd.Series(True, index=d.index))}", f"Inside ALL windows: {summ(inside)}",
           f"Outside: {summ(~inside)}",
           "", "Caution: historical association, not proven causation. Confirm with a controlled trial/DOE."]
    if inside.sum() < 30:
        gw.append("WARNING: very few points satisfy all windows simultaneously — window is not well-supported; relax to top drivers only.")
    open(os.path.join(a.outdir, "golden_window.md"), "w").write("\n".join(gw))

    # model importance with time-ordered split (assumes rows are time-ordered)
    n = len(d); cut = int(n * 0.7)
    m = GradientBoostingRegressor(random_state=0, max_depth=3, n_estimators=300, learning_rate=0.05, subsample=0.8)
    m.fit(d.loc[:cut - 1, a.x], y[:cut])
    r2_tr = m.score(d.loc[:cut - 1, a.x], y[:cut]); r2_te = m.score(d.loc[cut:, a.x], y[cut:])
    pi = permutation_importance(m, d.loc[cut:, a.x], y[cut:], n_repeats=10, random_state=0)
    imp = pd.DataFrame({"x": a.x, "perm_importance": pi.importances_mean, "sd": pi.importances_std}).sort_values("perm_importance", ascending=False)
    open(os.path.join(a.outdir, "importance.md"), "w").write(
        f"# Gradient boosting (train first 70% of rows, test last 30%)\n\nR² train={r2_tr:.3f}, test={r2_te:.3f}\n\n"
        + imp.round(4).to_markdown(index=False)
        + "\n\nIf test R² is much lower than train, the model learned regimes/periods, not stable physics.")

    top = imp["x"].tolist()[:6]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for ax, x in zip(axes.flat, top):
        pdp = partial_dependence(m, d[a.x], [a.x.index(x)], grid_resolution=30)
        ax.plot(pdp["grid_values"][0], pdp["average"][0], "b-")
        ax.axvspan(*win.get(x, (np.nan, np.nan)), color="green", alpha=0.15)
        for v in (a.lsl, a.usl):
            if v is not None: ax.axhline(v, color="red", ls="--", lw=0.8)
        ax.set_title(f"PDP {x} (green = golden window)", fontsize=9)
    for ax in list(axes.flat)[len(top):]: ax.axis("off")
    fig.tight_layout(); fig.savefig(os.path.join(a.outdir, "pdp.png"), dpi=120)

    k = min(4, len(wx)); fig, axes = plt.subplots(1, k, figsize=(4 * k, 3.5), squeeze=False)
    for ax, x in zip(axes[0], [r[0] for r in rows if r[0] in wx][:k]):
        ax.hist(d.loc[bad, x], bins=30, alpha=0.5, color="red", density=True, label="bad")
        ax.hist(d.loc[good, x], bins=30, alpha=0.5, color="green", density=True, label="good")
        lo, hi = win[x]; ax.axvline(lo, color="k", ls="--"); ax.axvline(hi, color="k", ls="--")
        ax.set_title(x, fontsize=9); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(a.outdir, "window_plot.png"), dpi=120)
    print("\n".join(out)); print(); print("\n".join(gw)); print(); print(imp.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
