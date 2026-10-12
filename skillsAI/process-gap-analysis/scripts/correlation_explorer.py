#!/usr/bin/env python3
"""Screen many X against Y with several correlation lenses.

Usage:
  python correlation_explorer.py --file data.csv --y SCT [--x a b c] \
      [--exclude id grade] [--group grade] [--control speed] \
      [--max-lag 30] [--nonlinear] [--outdir out]

Per X it reports: Pearson r, Spearman rho, BH-adjusted p, slope (Y units per X unit),
partial r controlling for --control vars, mutual information (--nonlinear),
best lag (--max-lag, rows), sign stability across time quarters, VIF.
Outputs: correlation_table.csv/.md, heatmap.png, top_scatter.png
"""
import argparse, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from scipy.cluster import hierarchy


def load(p):
    return pd.read_excel(p) if p.lower().endswith((".xlsx", ".xls")) else pd.read_csv(p)


def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n); out[o] = np.clip(q, 0, 1); return out


def partial_r(x, y, Z):
    Z = np.column_stack([np.ones(len(x)), Z])
    rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
    ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    return stats.pearsonr(rx, ry)[0]


def vif(X):
    X = (X - X.mean()) / X.std(ddof=0)
    out = {}
    for c in X.columns:
        others = X.drop(columns=c).values
        A = np.column_stack([np.ones(len(X)), others])
        beta = np.linalg.lstsq(A, X[c].values, rcond=None)[0]
        r2 = 1 - ((X[c].values - A @ beta) ** 2).sum() / ((X[c].values - X[c].mean()) ** 2).sum()
        out[c] = 1 / max(1 - r2, 1e-9)
    return out


def best_lag(x, y, max_lag):
    dx, dy = np.diff(x), np.diff(y)  # differencing avoids shared-trend spurious peaks
    best = (0, 0.0)
    for L in range(0, max_lag + 1):
        a, b = (dx[:-L], dy[L:]) if L else (dx, dy)
        if len(a) < 10: break
        r = np.corrcoef(a, b)[0, 1]
        if np.isfinite(r) and abs(r) > abs(best[1]): best = (L, r)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True); ap.add_argument("--y", required=True)
    ap.add_argument("--x", nargs="*"); ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--time"); ap.add_argument("--group")
    ap.add_argument("--control", nargs="*", default=[], help="confounders for partial correlation")
    ap.add_argument("--max-lag", type=int, default=0); ap.add_argument("--nonlinear", action="store_true")
    ap.add_argument("--top", type=int, default=6); ap.add_argument("--outdir", default="out")
    ap.add_argument("--query", help='pandas filter, e.g. "grade == \'KA125\' and speed > 500"')
    a = ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
    df = load(a.file)
    if a.query: df = df.query(a.query)
    if a.time and a.time in df:
        df[a.time] = pd.to_datetime(df[a.time], errors="coerce"); df = df.sort_values(a.time)
    num = df.select_dtypes("number")
    xs = a.x or [c for c in num.columns if c not in [a.y, *a.exclude, *a.control]]
    xs = [c for c in xs if num[c].nunique() > 1]
    rows = []
    for c in xs:
        d = df[[c, a.y, *a.control]].dropna()
        if len(d) < 10: continue
        x, y = d[c].values.astype(float), d[a.y].values.astype(float)
        pr, pp = stats.pearsonr(x, y); sr, sp = stats.spearmanr(x, y)
        slope = np.polyfit(x, y, 1)[0]
        row = {"x": c, "n": len(d), "pearson_r": pr, "pearson_p": pp, "spearman_rho": sr, "spearman_p": sp,
               "slope_y_per_x": slope, "delta_y_per_1sd_x": slope * x.std()}
        if a.control:
            row["partial_r"] = partial_r(x, y, d[a.control].values.astype(float))
        if a.max_lag:
            L, r = best_lag(x, y, a.max_lag); row["best_lag_rows"] = L; row["lag_r_diff"] = r
        if a.time and a.time in df:
            q = pd.to_datetime(df.loc[d.index, a.time]).dt.to_period("Q")
            signs = [np.sign(np.corrcoef(d.loc[q == k, c], d.loc[q == k, a.y])[0, 1])
                     for k in q.unique() if (q == k).sum() > 10]
            signs = [s for s in signs if np.isfinite(s)]
            row["sign_stability"] = (abs(sum(signs)) / len(signs)) if signs else np.nan
        if a.group and a.group in df:
            within = []
            for g, sub in df.loc[d.index].groupby(a.group):
                if len(sub) > 10 and sub[c].nunique() > 1:
                    within.append(stats.spearmanr(sub[c], sub[a.y])[0])
            row["median_within_group_rho"] = np.nanmedian(within) if within else np.nan
        rows.append(row)
    t = pd.DataFrame(rows)
    t["pearson_p_BH"] = bh(t["pearson_p"]); t["spearman_p_BH"] = bh(t["spearman_p"])
    t["pearson_minus_spearman"] = t["pearson_r"] - t["spearman_rho"]
    if a.nonlinear:
        from sklearn.feature_selection import mutual_info_regression
        d = df[t["x"].tolist() + [a.y]].dropna()
        mi = mutual_info_regression(d[t["x"]].values, d[a.y].values, random_state=0)
        t["mutual_info"] = mi
    X = df[t["x"]].dropna()
    if len(t) > 1 and len(X) > len(t) + 5:
        v = vif(X); t["VIF"] = t["x"].map(v)
    t = t.reindex(t["spearman_rho"].abs().sort_values(ascending=False).index)
    t.to_csv(os.path.join(a.outdir, "correlation_table.csv"), index=False)
    open(os.path.join(a.outdir, "correlation_table.md"), "w").write(t.round(4).to_markdown(index=False))

    # clustered heatmap
    cols = t["x"].tolist()[:30] + [a.y]
    C = df[cols].corr(method="spearman")
    if len(cols) > 2:
        link = hierarchy.linkage(1 - C.abs().fillna(0).values[np.triu_indices(len(C), 1)], "average")
        order = hierarchy.leaves_list(link); C = C.iloc[order, order]
    fig, ax = plt.subplots(figsize=(max(6, len(cols) * 0.4), max(5, len(cols) * 0.35)))
    im = ax.imshow(C.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(C))); ax.set_xticklabels(C.columns, rotation=90, fontsize=7)
    ax.set_yticks(range(len(C))); ax.set_yticklabels(C.index, fontsize=7)
    fig.colorbar(im); ax.set_title("Spearman correlation (clustered)"); fig.tight_layout()
    fig.savefig(os.path.join(a.outdir, "heatmap.png"), dpi=120)

    top = t["x"].tolist()[:a.top]
    n = len(top); ncol = 3; nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4 * ncol, 3.3 * nrow), squeeze=False)
    groups = df[a.group] if a.group and a.group in df else None
    for ax, c in zip(axes.flat, top):
        if groups is not None:
            for g in groups.dropna().unique():
                m = groups == g; ax.scatter(df.loc[m, c], df.loc[m, a.y], s=4, alpha=0.5, label=str(g))
            ax.legend(fontsize=6, markerscale=2)
        else:
            ax.scatter(df[c], df[a.y], s=4, alpha=0.4)
        # binned means (decile) to reveal shape
        d = df[[c, a.y]].dropna()
        try:
            b = pd.qcut(d[c], 10, duplicates="drop")
            bm = d.groupby(b, observed=True).agg(xm=(c, "mean"), ym=(a.y, "mean"))
            ax.plot(bm["xm"], bm["ym"], "k-o", ms=3, lw=1.2)
        except ValueError:
            pass
        r = t.set_index("x").loc[c, "spearman_rho"]
        ax.set_title(f"{c}  rho={r:.2f}", fontsize=9); ax.set_xlabel(c, fontsize=8); ax.set_ylabel(a.y, fontsize=8)
    for ax in list(axes.flat)[n:]: ax.axis("off")
    fig.tight_layout(); fig.savefig(os.path.join(a.outdir, "top_scatter.png"), dpi=120)
    print(t.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
