# Session Summary - DP Cooking ODL Analyzer

## Project Overview
This project involves analyzing ODL (Oxygen Delignification) data related to "DP Cooking". The goal is to analyze and prevent process variation between different digester batches. In the absence of a centralized quality database, the current strategy uses unsupervised clustering of operational parameters to identify patterns, drifts, and abnormalities in batch behavior.

## Current State
- **Workspace:** `C:\Data\Gemini CLI\DP Cooking ODL Analyzer`
- **Initial Data File:** `df_imported_PPPC_DPCooking.xlsx`
- **Visualizations Folder:** `visualizations/` (Contains 25 comparison plots)
- **Session Started:** Tuesday, May 26, 2026

## Progress Log
### 2026-05-26
- **Initialization:** Created `summary.md` for context tracking.
- **Data Review & Cleaning:** Cleaned status columns and handled sensor errors (NaN conversion).
- **Feature Engineering:** Extracted 900 Batch Signatures.
- **Clustering Analysis:** Flagged 45 "Abnormal" batches (top 5% by distance).
- **Variation Visualization:** Implemented `visualize_variation.py`.
    - Generated 25 boxplots comparing Normal vs Abnormal distributions.
    - **Key Driver Identification:** Discovered that Abnormal batches are primarily characterized by a massive drop in **Flow and Production**.
    - **Top Variation Drivers:**
        1. Deknotting Feed Flow (-43%)
        2. Screening Accept Flow (-40%)
        3. Production ODL (-38%)
        4. O2 Feed at Mixer 1 (-34%)
        5. Press 1 Consistency (-33%)

### 2026-06-05
- **Batch Variation Analysis:** Implemented `main_analysis.py` to quantify instability at the batch level.
- **SOP Violation Tracking:** Compared each batch signature against the 5th/95th percentile SOP limits.
- **Parameter-Specific Extremes:** Identified the "Worst Batch" for every individual parameter (e.g., the batch with the largest drop in consistency).
- **Digester Performance Heatmap:** Generated `digester_performance_heatmap.png` to visually benchmark D1-D4 performance across all parameters.
- **Integrity Verification:** Executed `integrity_check.py` which confirmed 100% mathematical accuracy between raw data signatures and final SOP violation reports.
- **Deliverables:** 
    1. `final_variation_analysis.xlsx`: Consolidated report with SOP limits, batch violations, and parameter leaders.
    2. `digester_performance_heatmap.png`: High-level diagnostic visual.
    3. `main_analysis.py`: Cleaned, production-ready analysis script.

### 2026-06-10
- **Digester Performance Comparison:** Implemented `visualize_digester_performance.py` to compare operational parameters across Digesters 1, 2, 3, and 4.
- **Double-Aspect Boxplots**: Generated side-by-side plots for each of the 27 parameters:
  - **Left subplot**: Distribution of **Batch Mean values** (revealing batch-to-batch variation and operational targets per digester).
  - **Right subplot**: Distribution of **Within-Batch Standard Deviations** (revealing process instability/volatility within individual runs).
- **Deliverables**:
  1. `visualizations_digester/`: 27 side-by-side PNG box plots with plotted overall means (diamonds) and automated text boxes displaying exact Mean, SD, and N for each digester.
  2. `digester_batch_performance_summary.xlsx`: Full statistical matrix covering count, means, standard deviations, mins, and maxes for both aspects.

### 2026-06-16
- **Sequential Phase Extension:** Integrated the new `Press1_BatchStatus` columns into the active analytical pipeline.
- **Data Robustness Upgrades:** Upgraded `clean_data.py` to seamlessly handle string-based sensor errors (`'No Data'`) via numeric coercion.
- **Sequential Window Search Overhaul:** Redesigned `extract_signatures.py` with a forward-scanning algorithm that extends each batch from the start of `Discharge` to the tail-end of `Press 1` washing. This seamlessly handles the expanded raw dataset (30,529 rows, 1,168 batches).
- **Statistical & Cluster Baseline Refresh:** Re-run `cluster_analysis.py`, `generate_sop_reference.py`, and `main_analysis.py` on the extended batch windows, identifying 59 Abnormal batches (top 5% by distance).
- **Physical Insights Discovered:**
  - **Digester 2** abnormality rate improved to **5.37%** (was 5.70%), as extended washing profiles proved many runs were stable over the combined window.
  - **Digester 4** abnormality rate rose to **7.14%** (was 5.60%), revealing more drift when evaluated across the full wash cycle.
- **Visual Asset Refresh:** Regenerated all 25+ comparison boxplots, 27 digester performance double-aspect plots, bell curves, and threshold logic diagrams.
- **Integrity Verification:** Run `integrity_check.py` which confirmed 100% mathematical accuracy on the new 1,168-batch definitions.
- **Deliverables**:
  1. `df_filtered_PPPC_DPCooking.xlsx`: Updated cleaned timeseries with 30,529 rows.
  2. `df_batch_signatures.xlsx`: Regenerated sequential batch signatures.
  3. `df_clustered_batches.xlsx`: Recalculated PCA coordinates and Normal/Abnormal flags.
  4. `sop_limits_reference.xlsx`: Restructured SOP operating windows.
  5. `final_variation_analysis.xlsx`: Updated sheets tracking SOP limits, batch violations, and extreme parameter leaders.
  6. `digester_performance_summary.xlsx`: Updated digester-specific abnormality and drift scores.
  7. Visual folders (`visualizations/`, `visualizations_bell/`, `visualizations_digester/`): Updated visual charts.

### 2026-07-07
- **Consumption Parameter Formulation:** Implemented row-by-row specific consumption calculations for Steam (`Specific Steam Consumption (t_ADT)`), White Liquor (`Specific WHLiqu Consumption (m3_ADT)`), O2 Mixer 1 (`Specific O2 Mixer 1 Consumption (kg_ADT)`), and O2 Pulp Heater (`Specific O2 Pulp Heater Consumption (kg_ADT)`) during timeseries extraction in `extract_signatures.py`. Coerced zero and offline production values to `NaN` to prevent division-by-zero errors.
- **Full Analytical Pipeline Update:** Executed the entire pipeline (`extract_signatures.py` -> `cluster_analysis.py` -> `generate_sop_reference.py` -> `main_analysis.py` -> `analyze_digester_performance.py` -> `visualize_variation.py` -> `visualize_digester_performance.py` -> `integrity_check.py`) to fully integrate the new parameters across all 31 process features.
- **Explanatory Mechanism Modeling:** Developed `visualize_consumption_logic.py` to scatter-plot the 1,168 actual batches against the theoretical $1/x$ consumption curve, proving the mathematical and physical logic of why process slowdowns trigger extreme resource waste.
- **Aesthetic Multi-Aspect Visualizers:**
  - Created `visualize_consumption_analysis.py` for comparative boxplot distributions of Steam Consumption and Volatility across digesters.
  - Created `visualize_chemical_consumption.py` to plot a 3x2 boxplot grid comparing Specific Consumption and Volatility for White Liquor, O2 Mixer 1, and O2 Pulp Heater.
  - Created `visualize_steam_bell_curve.py` for probability density comparison of Normal vs. Abnormal states against SOP limits.
  - Created `visualize_steam_bell_digester.py` and `visualize_chemical_bell_digester.py` to display digester-specific bell curve comparisons (KDE aspect) for Steam and Chemical consumption (incorporating the 70% headroom visual design).
- **Deliverables**:
  1. `visualizations/Specific_Steam_Consumption_Comparison.png` & `steam_consumption_analysis.xlsx`: Steam specific consumption averages and volatilities by digester.
  2. `visualizations/Specific_Chemical_Consumption_Comparison.png` & `chemical_consumption_analysis.xlsx`: Detailed 3x2 comparison grid of chemical averages and standard deviations.
  3. `visualizations_bell/Specific_Consumption_Logic_Explanatory.png`: Conceptual and real-data scatter overlay explaining the $y = C/x$ spike mechanism.
  4. `visualizations_bell/Specific_Steam_Consumption_Bell_Curve.png`: High-resolution probability density bell curve showing Normal and Abnormal states against SOP limits.
  5. `visualizations_digester/Specific_Steam_Consumption_t_ADT_bell_curves.png`: Side-by-side digester comparative bell curves (KDE aspect) for Specific Steam Consumption.
  6. `visualizations_digester/Specific_Chemical_Consumption_bell_curves.png`: 3x2 grid of digester comparative bell curves (KDE aspect) for all three chemical specific consumptions.
  7. Updated `final_variation_analysis.xlsx`, `digester_performance_summary.xlsx`, and visual folders containing all 31 process parameters.

## Important Details
- **The "Abnormal" Profile:** Abnormal batches represent significant process slowdowns or near-stops, not just small drifts.
- **Systemic Issue:** Flow, Production, O2, and Consistency all drop by ~30-40% simultaneously in abnormal batches, indicating production rate changes or partial shutdowns.
- **The Specific Resource Consumptions (The Top Variation Drivers):**
  - Specific chemical and steam consumptions represent the absolute strongest variation indicators in the system, taking the **top four spots** of all 31 parameters in terms of % differences between Normal and Abnormal states (O2 Pulp Heater: **+3,693%**, Steam: **+3,165%**, White Liquor: **+616%**, O2 Mixer 1: **+486%**).
  - This occurs because during process upsets/abnormalities, production slows down or halts, while heating and chemical feed rates are kept active (to keep vessels warm, or due to regulatory valve lag). This represents a major financial and resource waste.
- **The Digester Chemical Efficiency Gap (Control Loop Tuning Opportunities):**
  - Digesters 1 and 4 waste far more chemicals during abnormal batches than Digesters 2 and 3. 
  - For example, during abnormalities, White Liquor specific consumption spikes to **1.86 $m^3$/ADT** on Digester 4 (12x normal), but only to **0.48 $m^3$/ADT** on Digester 2. This shows that D2 has excellent interlock logic that successfully cuts back chemical flows during upsets, whereas D1 and D4 represent major loop-tuning targets.
- **Batch Instability:** Some batches exhibit up to 89% of parameters outside of normal operating windows.
- **Digester-Specific Performance Insights:**
  - **Digester 3 (D3) is the most stable and reliable**: It displays the lowest batch-to-batch variation (e.g., Production SD of 33.99 ADT/D) and low within-batch instability (Production within-batch SD of 6.43). It also operates at the highest average production rate (284.31 ADT/D).
  - **Digester 1 (D1) has the highest batch-to-batch variation**: It experiences the widest swings between runs (e.g., Production SD of 47.29 ADT/D) and is prone to severe dropouts (min production rate of 0.00 ADT/D).
  - **Digester 2 (D2) has the highest within-batch instability**: Although its batch averages are stable, the parameters fluctuate most wildly during the course of a single run (e.g., Production within-batch SD of 8.71, and Deknotting Flow within-batch SD of 39.94 m3/h).
- **The Variance vs. Violation Paradox (D1 vs D4):**
  - **Digester 1 (D1) has a "Reliability" (Trip/Dropout) Problem**: It operates very tightly on-target for most batches, but experiences a few severe process upsets where flow and production drop to zero. This heavily inflates its standard deviation (SD) but keeps its overall violation rate low (~11.6%).
  - **Digester 4 (D4) has a "Control Loop Tuning" (Drift) Problem**: It does not suffer from complete shutdowns, but its operating parameters are broadly dispersed and constantly drift on both sides of the SOP limit. This results in double the violation rate (~23.4%) despite having a lower standard deviation than D1.
- **Calculation Integrity:** Verified that SOP limits are derived exclusively from the "Normal" cluster and applied consistently across all ~900 batches.
- **Data Note:** Kappa online sensors were identified as zero/missing in this dataset; flow and pressure analyses remain valid.

## Next Steps
1. **Source Data Update:** Re-import data with active `Post O2 Kappa` sensor values to analyze quality impact.
2. **Correlation Analysis:** Investigate if specific upstream parameters (e.g., White Liquor flow) predict the transition into an "Abnormal" low-flow state.
3. **Drift Tracking:** Analyze if the "Normal" batches are drifting over time relative to the SOP targets.
4. **Steam & Chemical Efficiency Action Plan:** Investigate if control loops can automatically throttle steam and chemical flows when production rate drops below threshold limits to prevent the +3,150% steam and +3,690% chemical consumption spikes.
