"""
Pareto Front Analysis: Golden Batch Discovery

Find the optimal trade-off curve between Kappa (minimize) and Viscosity (maximize).
Uses 2-sigma filtering to remove outliers, then identifies the ideal point.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import spearmanr


def pareto_frontier(kappa, viscosity):
    """
    Compute Pareto front indices.
    A point (Kappa_i, Viscosity_i) is on the Pareto front if no other point
    has both lower Kappa AND higher Viscosity.
    
    Args:
        kappa: array of Kappa values
        viscosity: array of Viscosity values
    
    Returns:
        indices of points on the Pareto front
    """
    n = len(kappa)
    is_efficient = np.ones(n, dtype=bool)
    
    for i in range(n):
        if is_efficient[i]:
            # Check if any other point dominates i
            # Domination: lower Kappa AND higher Viscosity
            dominated = (kappa <= kappa[i]) & (viscosity >= viscosity[i])
            dominated[i] = False  # Exclude self
            is_efficient[dominated] = False
    
    return np.where(is_efficient)[0]


def find_knee_point(kappa_sorted, viscos_sorted):
    """Find knee point (highest curvature change in Pareto curve)."""
    if len(kappa_sorted) < 3:
        return 0
    
    dx = np.diff(kappa_sorted)
    dy = np.diff(viscos_sorted)
    
    # Avoid division by zero
    slope = np.divide(dy, dx, where=dx != 0, out=np.zeros_like(dy, dtype=float))
    
    if len(slope) < 2:
        return 0
    
    d_slope = np.diff(slope)
    knee_idx = np.argmax(np.abs(d_slope)) + 1
    return knee_idx


def find_ideal_point(kappa_sorted, viscos_sorted):
    """
    Find ideal point: closest to utopia (min Kappa, max Viscosity).
    Uses normalized Euclidean distance.
    """
    # Normalize to [0, 1]
    kappa_norm = (kappa_sorted - kappa_sorted.min()) / (kappa_sorted.max() - kappa_sorted.min() + 1e-10)
    viscos_norm = (viscos_sorted - viscos_sorted.min()) / (viscos_sorted.max() - viscos_sorted.min() + 1e-10)
    
    # Utopia: (0, 1) — min Kappa, max Viscosity
    distance_to_utopia = np.sqrt(kappa_norm**2 + (1 - viscos_norm)**2)
    ideal_idx = np.argmin(distance_to_utopia)
    
    return ideal_idx


def analyze_pareto(master_df, lab_linked_df, save_path="pareto_analysis.png"):
    """
    Complete Pareto front analysis for golden batch discovery.
    
    Args:
        master_df: batch_master dataframe
        lab_linked_df: lab_linked dataframe (long format: timestamp, parameter, value, digester, batch_id)
        save_path: path to save the output figure
    
    Returns:
        dict with analysis results
    """
    
    # Convert long format lab to wide format
    # lab_linked is: timestamp | parameter | value | digester | batch_id
    # pivot to: batch_id | press1_kappa | press1_viscosity | press1_brightness
    lab_pivot = lab_linked_df.pivot_table(
        index="batch_id",
        columns="parameter",
        values="value",
        aggfunc="mean"  # In case multiple samples per batch per parameter
    ).reset_index()
    
    # Fix: batch_id might have NaN from rows without a batch match
    lab_pivot = lab_pivot.dropna(subset=["batch_id"])
    lab_pivot["batch_id"] = lab_pivot["batch_id"].astype(int)
    
    # Combine with master (master already has press1_* columns, so use suffix to avoid conflict)
    data = master_df.merge(lab_pivot, on="batch_id", how="inner", suffixes=("_master", "_lab"))
    
    # Use lab values from pivot (prefer _lab over _master when both exist)
    kappa_col = "press1_kappa_lab" if "press1_kappa_lab" in data.columns else "press1_kappa"
    viscos_col = "press1_viscosity_lab" if "press1_viscosity_lab" in data.columns else "press1_viscosity"
    brightness_col = "press1_brightness_lab" if "press1_brightness_lab" in data.columns else "press1_brightness"
    
    data = data.dropna(subset=[kappa_col, viscos_col])
    
    kappa_all = data[kappa_col].values
    viscos_all = data[viscos_col].values
    
    # ===== STEP 1: Filter by 2-sigma =====
    kappa_mean = kappa_all.mean()
    kappa_std = kappa_all.std()
    kappa_2sigma_lo = kappa_mean - 2 * kappa_std
    kappa_2sigma_hi = kappa_mean + 2 * kappa_std
    
    viscos_mean = viscos_all.mean()
    viscos_std = viscos_all.std()
    viscos_2sigma_lo = viscos_mean - 2 * viscos_std
    viscos_2sigma_hi = viscos_mean + 2 * viscos_std
    
    clean_mask = (
        (kappa_all >= kappa_2sigma_lo) & (kappa_all <= kappa_2sigma_hi) &
        (viscos_all >= viscos_2sigma_lo) & (viscos_all <= viscos_2sigma_hi)
    )
    
    kappa_clean = kappa_all[clean_mask]
    viscos_clean = viscos_all[clean_mask]
    data_clean = data[clean_mask].reset_index(drop=True)
    
    # ===== STEP 2: Compute Pareto front =====
    pareto_idx_all = pareto_frontier(kappa_all, viscos_all)
    pareto_idx_clean = pareto_frontier(kappa_clean, viscos_clean)
    
    # Sort by Kappa for plotting
    pareto_order_all = pareto_idx_all[np.argsort(kappa_all[pareto_idx_all])]
    pareto_order_clean = pareto_idx_clean[np.argsort(kappa_clean[pareto_idx_clean])]
    
    kappa_pareto_all = kappa_all[pareto_order_all]
    viscos_pareto_all = viscos_all[pareto_order_all]
    kappa_pareto_clean = kappa_clean[pareto_order_clean]
    viscos_pareto_clean = viscos_clean[pareto_order_clean]
    
    # ===== STEP 3: Find ideal point =====
    ideal_idx_clean = find_ideal_point(kappa_pareto_clean, viscos_pareto_clean)
    ideal_kappa = kappa_pareto_clean[ideal_idx_clean]
    ideal_viscos = viscos_pareto_clean[ideal_idx_clean]
    ideal_batch_idx = pareto_order_clean[ideal_idx_clean]
    
    # ===== STEP 4: Plot =====
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # LEFT: Before filtering
    ax = axes[0]
    ax.scatter(kappa_all, viscos_all, alpha=0.3, s=30, color="gray", label="All batches")
    ax.plot(kappa_pareto_all, viscos_pareto_all, "r--", linewidth=2, label="Pareto front (all)")
    ax.scatter(kappa_pareto_all, viscos_pareto_all, s=100, color="red", marker="o", zorder=5)
    
    # 2-sigma bands
    ax.axvline(kappa_2sigma_lo, color="orange", linestyle=":", alpha=0.5)
    ax.axvline(kappa_2sigma_hi, color="orange", linestyle=":", alpha=0.5, label=f"2σ Kappa")
    ax.axhline(viscos_2sigma_lo, color="purple", linestyle=":", alpha=0.5)
    ax.axhline(viscos_2sigma_hi, color="purple", linestyle=":", alpha=0.5, label=f"2σ Viscosity")
    
    ax.set_xlabel("Kappa (↓ better)", fontsize=11)
    ax.set_ylabel("Viscosity (↑ better)", fontsize=11)
    ax.set_title(f"Before 2σ filter\n(N={len(kappa_all)} batches)", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9, loc="best")
    ax.grid(True, alpha=0.3)
    
    # RIGHT: After filtering
    ax = axes[1]
    ax.scatter(kappa_clean, viscos_clean, alpha=0.4, s=30, color="blue", label="Clean batches (2σ)")
    ax.plot(kappa_pareto_clean, viscos_pareto_clean, "r--", linewidth=2, label="Pareto front (clean)")
    ax.scatter(kappa_pareto_clean, viscos_pareto_clean, s=100, color="red", marker="o", zorder=5)
    
    # Ideal point
    ax.scatter([ideal_kappa], [ideal_viscos], s=400, color="gold", marker="*", 
               zorder=10, edgecolor="black", linewidth=2,
               label=f"Ideal: Kappa={ideal_kappa:.2f}, Visc={ideal_viscos:.0f}")
    
    ax.set_xlabel("Kappa (↓ better)", fontsize=11)
    ax.set_ylabel("Viscosity (↑ better)", fontsize=11)
    ax.set_title(f"After 2σ filter\n(N={len(kappa_clean)} batches, Pareto={len(pareto_idx_clean)})", 
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9, loc="best")
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=100, bbox_inches="tight")
    plt.show()
    
    # ===== STEP 5: Characterize ideal batch and nearby =====
    # Get golden batches: Pareto + within 5% of ideal point (normalized distance)
    kappa_norm = (kappa_clean - kappa_clean.min()) / (kappa_clean.max() - kappa_clean.min() + 1e-10)
    viscos_norm = (viscos_clean - viscos_clean.min()) / (viscos_clean.max() - viscos_clean.min() + 1e-10)
    
    ideal_kappa_norm = (ideal_kappa - kappa_clean.min()) / (kappa_clean.max() - kappa_clean.min() + 1e-10)
    ideal_viscos_norm = (ideal_viscos - viscos_clean.min()) / (viscos_clean.max() - viscos_clean.min() + 1e-10)
    
    distance_to_ideal = np.sqrt((kappa_norm - ideal_kappa_norm)**2 + (viscos_norm - ideal_viscos_norm)**2)
    golden_threshold = 0.10  # 5% of normalized space
    golden_mask = distance_to_ideal <= golden_threshold
    golden_batches = data_clean[golden_mask].copy()
    
    print("\n" + "="*80)
    print("PARETO FRONT ANALYSIS RESULTS")
    print("="*80)
    print(f"\nFiltering by 2-sigma:")
    print(f"  Kappa: {kappa_mean:.2f} ± {kappa_std:.2f} → [{kappa_2sigma_lo:.2f}, {kappa_2sigma_hi:.2f}]")
    print(f"  Viscosity: {viscos_mean:.0f} ± {viscos_std:.0f} → [{viscos_2sigma_lo:.0f}, {viscos_2sigma_hi:.0f}]")
    print(f"  Removed: {(~clean_mask).sum()} outliers")
    print(f"  Kept: {clean_mask.sum()} batches")
    
    print(f"\nPareto front (clean data):")
    print(f"  Points on front: {len(pareto_idx_clean)}")
    print(f"  Kappa range: {kappa_pareto_clean.min():.2f} – {kappa_pareto_clean.max():.2f}")
    print(f"  Viscosity range: {viscos_pareto_clean.min():.0f} – {viscos_pareto_clean.max():.0f}")
    
    print(f"\nIdeal point (closest to utopia):")
    print(f"  Kappa: {ideal_kappa:.2f}")
    print(f"  Viscosity: {ideal_viscos:.0f}")
    print(f"  Digester: D{int(data_clean.iloc[ideal_batch_idx]['digester'])}")
    
    print(f"\nGolden batches (within 5% of ideal):")
    print(f"  Count: {len(golden_batches)}")
    if len(golden_batches) > 0:
        print(f"  Kappa: {golden_batches[kappa_col].mean():.2f} ± {golden_batches[kappa_col].std():.2f}")
        print(f"  Viscosity: {golden_batches[viscos_col].mean():.0f} ± {golden_batches[viscos_col].std():.0f}")
        print(f"  By digester:\n{golden_batches.groupby('digester').size()}")
    
    print("\n" + "="*80 + "\n")
    
    return {
        "data_all": data,
        "data_clean": data_clean,
        "kappa_all": kappa_all,
        "viscos_all": viscos_all,
        "kappa_clean": kappa_clean,
        "viscos_clean": viscos_clean,
        "kappa_2sigma": (kappa_2sigma_lo, kappa_2sigma_hi),
        "viscos_2sigma": (viscos_2sigma_lo, viscos_2sigma_hi),
        "pareto_idx_all": pareto_idx_all,
        "pareto_idx_clean": pareto_idx_clean,
        "ideal_kappa": ideal_kappa,
        "ideal_viscos": ideal_viscos,
        "ideal_batch_idx": ideal_batch_idx,
        "golden_batches": golden_batches,
        "golden_mask": golden_mask
    }


if __name__ == "__main__":
    # Example: run from notebook
    # from build_master import load_outputs
    # master, lab_linked = load_outputs()
    # results = analyze_pareto(master, lab_linked)
    pass
