"""
Charts for 01_compare.ipynb. Each function draws one figure, saves a PNG into
config.OUTPUT_DIR and returns the figure.
"""
import os

import matplotlib.pyplot as plt
import numpy as np
import shap

import config
import explain
from data import label

# Colors (categorical slots 1-2, neutral ink, accept-band tint)
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID, BAND = "#0b0b0b", "#52514e", "#e4e3df", "#cde2fb"

plt.rcParams.update({
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "font.size": 10,
})


def _save(fig, name):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(config.OUTPUT_DIR, name)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    print(f"  saved {path}")
    return fig


def leaderboard_bar(board):
    """Out-of-time R^2 per model variant, with the gate line."""
    b = board.iloc[::-1]
    names = [f"{m}  ({f})" for m, f in zip(b["model"], b["features"])]
    fig, ax = plt.subplots(figsize=(7, 0.4 * len(b) + 1.2))
    ax.barh(names, b["R2"], color=BLUE, height=0.6)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.axvline(config.GATE_R2, color=INK, lw=1, ls="--")
    ax.text(config.GATE_R2, len(b) - 0.4, f"gate {config.GATE_R2} ", color=INK, va="bottom", ha="right")
    for i, (r2, mae) in enumerate(zip(b["R2"], b["MAE"])):
        ax.text(max(r2, 0) + 0.005, i, f"{r2:.2f}  (MAE {mae})", va="center", color=MUTED, fontsize=9)
    ax.set_xlabel(f"Out-of-time R² ({config.CV_FOLDS}-fold TimeSeriesSplit)")
    ax.set_title(f"{config.TARGET_LABEL}: model leaderboard", loc="left", color=INK)
    ax.grid(axis="y", visible=False)
    return _save(fig, "leaderboard.png")


def predicted_vs_actual(df, pred, model_name):
    """Actual lab value vs out-of-time prediction along time."""
    ok = pred.notna()
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.plot(df.loc[ok, "batch_start"], df.loc[ok, config.TARGET], "o", ms=3, color=BLUE, label="Actual (lab)")
    ax.plot(df.loc[ok, "batch_start"], pred[ok], "-", lw=2, color=ORANGE, label=f"Predicted ({model_name})")
    lo, hi = config.TARGET_BAND
    ax.axhspan(lo, hi, color=BAND, alpha=0.5, lw=0)
    ax.set_ylabel(config.TARGET_LABEL)
    ax.set_title(f"{config.TARGET_LABEL}: actual vs out-of-time prediction (band = {lo}-{hi})",
                 loc="left", color=INK)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.08), ncol=2)
    return _save(fig, f"pred_vs_actual_{model_name}.png")


def shap_summary(df, feats):
    """XGBoost SHAP beeswarm on the hold-out (each dot = one batch)."""
    sv, _ = explain.shap_values(df, feats)
    plt.figure()
    shap.plots.beeswarm(sv, max_display=len(feats), show=False)
    fig = plt.gcf()
    fig.axes[0].set_title(f"{config.TARGET_LABEL}: XGBoost SHAP (hold-out, last {int(config.TEST_SHARE*100)}%)",
                          loc="left", color=INK)
    return _save(fig, "shap_summary.png")


def pdp_top(df, feats, effects):
    """Partial dependence (XGBoost, fit on all rows) for the top N process features, with the accept band."""
    from models import make_model
    top = [f for f in effects.index if not f.startswith("is_D")][:config.TOP_N_PDP]
    mdl = make_model("xgboost").fit(df[feats], df[config.TARGET])
    fig, axes = plt.subplots(1, len(top), figsize=(4.2 * len(top), 3.4), sharey=True)
    axes = np.atleast_1d(axes)
    lo, hi = config.TARGET_BAND
    for ax, f in zip(axes, top):
        grid = np.linspace(df[f].quantile(0.05), df[f].quantile(0.95), 40)
        X = df[feats].copy()
        avg = []
        for v in grid:
            X[f] = v
            avg.append(mdl.predict(X).mean())
        ax.axhspan(lo, hi, color=BAND, alpha=0.5, lw=0)
        ax.plot(grid, avg, color=BLUE, lw=2)
        inside = df[f].between(grid[0], grid[-1])   # rug = where the batches are
        ax.plot(df.loc[inside, f], np.full(inside.sum(), ax.get_ylim()[0]), "|", color=MUTED, alpha=0.3, ms=8)
        ax.set_xlim(grid[0], grid[-1])
        ax.set_xlabel(label(f))
    axes[0].set_ylabel(f"Predicted {config.TARGET_LABEL}")
    fig.suptitle(f"{config.TARGET_LABEL}: partial dependence, top {len(top)} features (P5-P95 of data)",
                 x=0.01, ha="left", color=INK)
    fig.tight_layout()
    return _save(fig, "pdp_top.png")


# ---------------------------------------------------------------- golden window (02_golden_window.ipynb)
def fail_curves(df, res, event="fail", top=6):
    """Fail rate per quintile of the top X (bars with Wilson 95% CI); the cut and its range in the title."""
    import golden
    rows = res.head(top)
    ncol = 3
    nrow = int(np.ceil(len(rows) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 3.5 * nrow), sharey=True)
    axes = np.atleast_1d(axes).ravel()
    base = df[event].mean()
    for ax, r in zip(axes, rows.itertuples()):
        c = golden.curve(df, r.x, event)
        pos = np.arange(len(c))
        bad = (c["x_hi"] <= r.cut) if r.side == "<=" else (c["x_lo"] > r.cut)
        ax.bar(pos, c["fail_rate"], width=0.8, color=[ORANGE if b else BLUE for b in bad])
        ax.errorbar(pos, c["fail_rate"], yerr=[c["fail_rate"] - c["ci_lo"], c["ci_hi"] - c["fail_rate"]],
                    fmt="none", ecolor=INK, elinewidth=1, capsize=3)
        ax.axhline(base, color=MUTED, lw=1, ls="--")
        ax.set_xticks(pos, [f"{a:.3g}-{b:.3g}" for a, b in zip(c["x_lo"], c["x_hi"])], rotation=25, fontsize=8)
        ax.set_title(f"{r.label}  [grade {r.grade}]\nbad side {r.bad_side}  (cut range {r.cut_p5:.3g}-{r.cut_p95:.3g})",
                     loc="left", fontsize=10, color=INK)
        ax.set_ylim(0, 1)
        ax.grid(axis="x", visible=False)
    for ax in axes[len(rows):]:
        ax.set_visible(False)
    for ax in axes[::ncol]:
        ax.set_ylabel(f"{golden.OUTCOMES[event]} rate")
    fig.suptitle(f"{golden.OUTCOMES[event]} rate per quintile of X (95% CI). Orange = bins on the bad side "
                 f"of the cut. Dashed = overall {base:.0%}", x=0.01, ha="left", color=INK)
    fig.tight_layout()
    return _save(fig, f"golden_curves_{event}.png")


def window_months(per_month, title, name="golden_window_months.png"):
    """Fail rate inside vs outside the window, month by month (the season check)."""
    x = np.arange(len(per_month))
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.bar(x - 0.2, per_month["fail_outside"], 0.38, color=ORANGE, label="Outside window")
    ax.bar(x + 0.2, per_month["fail_inside"], 0.38, color=BLUE, label="Inside window")
    for i, r in enumerate(per_month.itertuples()):
        ax.text(i - 0.2, r.fail_outside + 0.02, f"{r.fail_outside:.0%}\nn={r.n_outside}", ha="center", fontsize=8, color=MUTED)
        ax.text(i + 0.2, r.fail_inside + 0.02, f"{r.fail_inside:.0%}\nn={r.n_inside}", ha="center", fontsize=8, color=MUTED)
    ax.set_xticks(x, per_month["month"])
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Fail QC rate")
    ax.set_title(title, loc="left", color=INK)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.12), ncol=2)
    ax.grid(axis="x", visible=False)
    return _save(fig, name)
