#!/usr/bin/env python3
"""Discover operating regimes by clustering process X, then profile quality Y per regime.

Usage:
  python cluster_regimes.py --file data.csv --y SCT --x speed refining starch ... \
      [--lsl 2.5 --usl 3.5] [--method kmeans|gmm|dbscan] [--k 0 (auto)] [--outdir out]

Clusters on X only (never on Y). Auto-selects k by silhouette (kmeans) or BIC (gmm).
Outputs: cluster_profile.md/.csv, clusters_pca.png, cluster_y_box.png, data_with_cluster.csv
"""
import argparse, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score


def load(p):
    return pd.read_excel(p) if p.lower().endswith((".xlsx", ".xls")) else pd.read_csv(p)


def cpk(y, lsl, usl):
    y = y.dropna(); mu = y.mean()
    s = np.abs(np.diff(y.values)).mean() / 1.128 if len(y) > 2 else y.std()
    c = []
    if usl is not None: c.append((usl - mu) / (3 * s))
    if lsl is not None: c.append((mu - lsl) / (3 * s))
    return min(c) if c and s > 0 else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True); ap.add_argument("--y", required=True)
    ap.add_argument("--x", nargs="+", required=True)
    ap.add_argument("--lsl", type=float); ap.add_argument("--usl", type=float)
    ap.add_argument("--method", default="kmeans", choices=["kmeans", "gmm", "dbscan"])
    ap.add_argument("--k", type=int, default=0); ap.add_argument("--kmax", type=int, default=8)
    ap.add_argument("--eps", type=float, default=0.8); ap.add_argument("--group")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--query", help='pandas filter, e.g. "grade == \'KA125\' and speed > 500"')
    a = ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
    df = load(a.file)
    if a.query: df = df.query(a.query)
    d = df.dropna(subset=a.x + [a.y]).copy()
    Z = StandardScaler().fit_transform(d[a.x].values)
    sample = np.random.default_rng(0).choice(len(Z), min(len(Z), 5000), replace=False)
    info = []
    if a.method == "kmeans":
        if a.k:
            k = a.k
        else:
            scores = {}
            for k in range(2, a.kmax + 1):
                lab = KMeans(k, n_init=10, random_state=0).fit_predict(Z)
                scores[k] = silhouette_score(Z[sample], lab[sample])
            k = max(scores, key=scores.get); info.append(f"silhouette by k: { {kk: round(v,3) for kk,v in scores.items()} }")
        labels = KMeans(k, n_init=10, random_state=0).fit_predict(Z)
    elif a.method == "gmm":
        if a.k:
            k = a.k
        else:
            bics = {k: GaussianMixture(k, random_state=0).fit(Z).bic(Z) for k in range(1, a.kmax + 1)}
            k = min(bics, key=bics.get); info.append(f"BIC by k: { {kk: round(v) for kk,v in bics.items()} }")
        labels = GaussianMixture(k, random_state=0).fit(Z).predict(Z)
    else:
        labels = DBSCAN(eps=a.eps, min_samples=max(5, len(Z) // 200)).fit_predict(Z)
        info.append("DBSCAN label -1 = noise/abnormal points")
    d["cluster"] = labels

    rows = []
    for c, sub in d.groupby("cluster"):
        r = {"cluster": c, "n": len(sub), "share_%": 100 * len(sub) / len(d),
             f"{a.y}_mean": sub[a.y].mean(), f"{a.y}_std": sub[a.y].std(), "Cpk": cpk(sub[a.y], a.lsl, a.usl)}
        oos = np.zeros(len(sub), bool)
        if a.lsl is not None: oos |= sub[a.y].values < a.lsl
        if a.usl is not None: oos |= sub[a.y].values > a.usl
        r["%OOS"] = 100 * oos.mean()
        for x in a.x: r[f"{x}_med"] = sub[x].median()
        rows.append(r)
    prof = pd.DataFrame(rows).sort_values("Cpk", ascending=False)
    txt = ["# Cluster profile (clustered on X only)", "", *info, "", prof.round(3).to_markdown(index=False)]
    if a.group and a.group in d:
        txt += ["", f"## Cluster × {a.group} cross-tab (check clusters aren't just {a.group})", "",
                pd.crosstab(d["cluster"], d[a.group]).to_markdown()]
    # which X separate best vs worst cluster (standardized difference)
    if len(prof) >= 2:
        best, worst = prof.iloc[0]["cluster"], prof.iloc[-1]["cluster"]
        diff = {x: (d.loc[d.cluster == best, x].mean() - d.loc[d.cluster == worst, x].mean()) / d[x].std() for x in a.x}
        s = pd.Series(diff).sort_values(key=np.abs, ascending=False)
        txt += ["", f"## X difference best cluster {best} vs worst {worst} (in σ units)", "", s.round(3).to_markdown()]
    open(os.path.join(a.outdir, "cluster_profile.md"), "w").write("\n".join(txt))
    prof.to_csv(os.path.join(a.outdir, "cluster_profile.csv"), index=False)
    d.to_csv(os.path.join(a.outdir, "data_with_cluster.csv"), index=False)

    P = PCA(2).fit(Z); pc = P.transform(Z)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    for c in sorted(d["cluster"].unique()):
        m = labels == c; a1.scatter(pc[m, 0], pc[m, 1], s=5, alpha=0.5, label=f"C{c}")
    a1.legend(markerscale=3); a1.set_title(f"Clusters in PCA space (var expl {P.explained_variance_ratio_.sum():.0%})")
    sc = a2.scatter(pc[:, 0], pc[:, 1], c=d[a.y], s=5, cmap="viridis"); fig.colorbar(sc, ax=a2)
    a2.set_title(f"Colored by {a.y}")
    for i, x in enumerate(a.x):  # loadings
        a2.arrow(0, 0, P.components_[0, i] * 3, P.components_[1, i] * 3, color="r", width=0.01)
        a2.text(P.components_[0, i] * 3.3, P.components_[1, i] * 3.3, x, fontsize=7, color="r")
    fig.tight_layout(); fig.savefig(os.path.join(a.outdir, "clusters_pca.png"), dpi=120)

    fig, ax = plt.subplots(figsize=(8, 4))
    cl = sorted(d["cluster"].unique())
    ax.boxplot([d.loc[d.cluster == c, a.y] for c in cl], tick_labels=[f"C{c}" for c in cl])
    for v in (a.lsl, a.usl):
        if v is not None: ax.axhline(v, color="red", ls="--")
    ax.set_title(f"{a.y} by regime"); fig.tight_layout(); fig.savefig(os.path.join(a.outdir, "cluster_y_box.png"), dpi=120)
    print("\n".join(txt))


if __name__ == "__main__":
    main()
