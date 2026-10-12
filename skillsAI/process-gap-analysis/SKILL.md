---
name: process-gap-analysis
description: Deep statistical analysis of manufacturing process data to find gaps between current and target quality, explain what drives quality variation, and propose operating windows or settings to optimize. Use this skill whenever the user wants to analyze process or quality data (CSV/Excel/Power BI export), find why a product misses spec, compare good vs bad runs, find correlations between many parameters, cluster operating regimes, check process capability (Cp/Cpk), SPC/control charts, 2-sigma/3-sigma limits, histograms, outliers, root cause, golden batch, or "what setting gives the best quality" — even if they only say things like "หา gap", "ทำไมคุณภาพไม่นิ่ง", "ค่าไหนมีผลกับ quality", "optimize เครื่อง", or paste a table of sensor/lab readings. Covers paper machines and general continuous or batch manufacturing.
---

# Process Gap Analysis

Turn raw process + quality data into a defensible answer to three questions:

1. **Where is the gap?** How far is the quality characteristic from target/spec, how often, and when.
2. **What drives it?** Which parameters (and which combinations, regimes, time lags) explain the variation.
3. **What should change?** A concrete operating window or setting change, with the evidence and its confidence.

The core discipline: **never trust a single method.** Every important conclusion should be seen from at least two different angles (e.g., a correlation *and* a cluster profile *and* a good-vs-bad comparison). When methods disagree, that disagreement is itself a finding — report it and explain it.

Reply in the user's language (often Thai with English technical terms). Keep statistical terms in English.

---

## Step 0 — Frame the problem before touching numbers

Establish (ask only for what is missing and actually blocks the analysis; otherwise state assumptions and proceed):

- **Response (Y / CTQ)**: which quality variable(s) matter. Target, LSL, USL. One-sided or two-sided spec?
- **Candidate drivers (X)**: process parameters, raw material properties, settings, environment.
- **Unit of analysis**: timestamp (continuous), reel/batch/lot, shift, grade/product.
- **Grouping variables**: grade/product, machine, line, crew, raw-material supplier. Analyses that mix grades usually produce fake correlations — split or normalize by grade first.
- **Process lag**: how long between changing X and seeing it in Y (e.g., wet end → reel, lab test delay). If unknown, estimate it with lagged cross-correlation (see methods).
- **Controllable vs. not**: separate knobs operators can turn from disturbances they can't. Recommendations must only move controllable X.

Write this framing as a short "Problem statement" at the top of the output.

---

## Step 1 — Data audit (always do this; it changes conclusions more than any model)

Run `scripts/profile_data.py` first. Check and report:

- Rows, time span, sampling interval, missing % per column, constant / near-constant columns.
- Downtime, grade changes, startup/shutdown, sheet breaks — these must be flagged and usually excluded, or they dominate every statistic.
- Sensor faults: flatlines, stuck values, impossible values, sudden unit changes.
- Mixed sampling rates (1-sec DCS vs. lab once per reel): align to the slowest meaningful unit, aggregating X with mean/std over the window, respecting the lag.
- Autocorrelation: consecutive time-series points are not independent. p-values from naive tests will be overconfident; prefer effect sizes, block-level aggregation, or time-split validation.

State clearly what was removed and why, with row counts before/after.

---

## Step 2 — Describe the gap (distribution & capability)

For each Y:

- Histogram + KDE, with LSL/USL/target lines. Look at shape: normal, skewed, **bimodal** (bimodal almost always means two regimes/grades/crews mixed — go find them), heavy tails.
- Mean, std, median, IQR, skewness, kurtosis, normality test (Shapiro on sample / Anderson-Darling).
- **Capability**: Cp, Cpk (within/short-term σ from moving range), Pp, Ppk (overall σ). A big Cp–Cpk gap = off-center (fix the mean); low Cp = too much spread (fix variation). A big Pp vs Cp gap = process drifts over time.
- % out of spec actual vs. predicted from the fitted distribution; ppm.
- **Sigma bands**: mean ± 1σ/2σ/3σ, % of points beyond each vs. what a normal distribution expects (4.6% beyond 2σ, 0.27% beyond 3σ). Excess beyond 2σ indicates special causes.
- **Control chart** (I-MR or X̄-R by batch) with Western Electric / Nelson rules to separate common-cause from special-cause variation. Mark when violations happen and line them up with events.

Quantify the gap in one sentence: e.g., "Cpk = 0.82 vs target 1.33; mean is 0.6σ below target; 7.4% out of spec, mostly on night shift after grade change."

---

## Step 3 — Find drivers: use several lenses

Pick methods from this menu based on data size and question. Default path for a first pass: **correlation screen → good-vs-bad comparison → clustering/regime → multivariate model → confirm**. Details, formulas, pitfalls, and when to use each are in `references/methods.md` — read the relevant section before applying a method you aren't using routinely.

| Lens | Question it answers | Script / method |
|---|---|---|
| Correlation matrix (Pearson + Spearman) | Which X move linearly / monotonically with Y? | `scripts/correlation_explorer.py` |
| Mutual information / distance correlation | Non-linear relationships Pearson misses | `correlation_explorer.py --nonlinear` |
| Partial correlation | Is X→Y real or both driven by Z (e.g., speed)? | methods.md §3.3 |
| Lagged cross-correlation | What's the delay between X and Y? | `correlation_explorer.py --max-lag` |
| Multicollinearity (VIF, correlation clusters) | Which X are redundant copies of each other? | `correlation_explorer.py` |
| Good-vs-bad comparison (Mann-Whitney, effect size, KS) | Which X differ most between in-spec and out-of-spec? | `scripts/golden_window.py` |
| Binning / quantile analysis | At what X range does Y go bad? Thresholds? | `golden_window.py` |
| Clustering (k-means, GMM, DBSCAN/HDBSCAN) | Are there distinct operating regimes, and which one gives best quality? | `scripts/cluster_regimes.py` |
| PCA / PLS | What combinations of X explain Y? Reduce 50 tags to 3–5 factors | methods.md §5 |
| Regression (OLS, Lasso) | Size and sign of each effect, holding others fixed | methods.md §6 |
| Tree models (Random Forest / Gradient Boosting) + permutation importance / SHAP / PDP | Non-linear effects, interactions, thresholds | methods.md §6.3 |
| Change-point detection | When did the process shift, and what changed then? | methods.md §7 |
| ANOVA / Kruskal-Wallis | Does Y differ by grade, crew, supplier, machine? | methods.md §4 |
| Golden batch / best operating envelope | What X ranges do the best runs share? | `golden_window.py` |

Rules of thumb:
- Always look at scatter plots of top pairs; one outlier or two grades can create or hide a correlation (Simpson's paradox).
- Use Spearman alongside Pearson. A big difference between them signals non-linearity or outliers.
- |r| < 0.3 in noisy plant data can still be important if the X is controllable and the effect size in engineering units is large — report slope in real units, not only r.
- With many X, control false discoveries (Benjamini-Hochberg) or validate on a held-out time period.
- Validate models with **time-based splits** (train on earlier months, test on later), never random splits for time series.

---

## Step 4 — Triangulate and explain

Build a **driver evidence table**: one row per candidate X, columns for each lens (correlation, good-vs-bad effect size, cluster difference, model importance, lag found), plus physical plausibility. Rank drivers by *agreement across lenses × controllability × effect size in engineering units*.

Then challenge the top findings:
- Could it be reverse causation (operator reacts to bad Y by moving X)? Check lag direction.
- Could a confounder explain it (speed, grade, season, raw material)? Check partial correlation or within-group analysis.
- Is it only true in one regime/grade?
- Does it make physical/engineering sense? If not, flag it as a hypothesis to test, not a conclusion.

---

## Step 5 — Optimize / recommend

Translate drivers into action:
- **Operating window**: recommended ranges for key X (from golden-window / cluster of best runs), with how much of historical data already sits inside it and the quality achieved there.
- **Expected improvement**: estimate new mean, σ, Cpk, % out-of-spec if operated inside the window (from historical subset or model prediction), with uncertainty. Be conservative — historical data ≠ controlled experiment.
- **Trade-offs**: effect on other quality variables, energy, speed/throughput, cost.
- **Next validation step**: a small controlled trial or DOE (2-level factorial on the top 2–4 X, or response surface) to confirm causality before permanent change. See methods.md §8.
- **Monitoring**: which X/Y to put on control charts or a Power BI dashboard, with alert limits.

---

## Output structure

Use this structure for a full analysis (shorten for quick questions):

1. **Problem statement & assumptions**
2. **Data audit** — what was kept/removed, quality issues
3. **Gap quantification** — distribution, capability, control-chart findings (with charts)
4. **Driver analysis** — findings from each lens, with charts
5. **Driver evidence table** — triangulated ranking
6. **Recommendations** — operating window, expected gain, trade-offs, validation plan, monitoring
7. **Limitations & open questions**

Charts: save PNGs and show them. Prefer histogram with spec lines, control chart, correlation heatmap (clustered), top scatter plots colored by grade/cluster, cluster profile chart, and operating-window chart.

When the user wants to take it into Power BI, also offer: the cleaned dataset, calculated columns/measures (e.g., DAX for Cpk, sigma bands, in-spec flag), and which visuals to build.

---

## Scripts quick reference

All scripts read .csv/.xlsx, write markdown tables + PNGs to `--outdir`, and accept `--query` (pandas filter, e.g. `"grade == 'KA150'"`) so every analysis can be run per grade/product. Rows are assumed time-ordered (sort first).

```bash
S=<skill_dir>/scripts
python $S/profile_data.py --file d.csv --y Y --lsl L --usl U --target T --time ts --group grade --outdir o/profile
python $S/correlation_explorer.py --file d.csv --y Y --exclude id --time ts --group grade \
    --control speed --max-lag 30 --nonlinear --outdir o/corr
python $S/cluster_regimes.py --file d.csv --y Y --x x1 x2 x3 --lsl L --usl U --group grade --outdir o/cluster
python $S/golden_window.py --file d.csv --y Y --x x1 x2 x3 --lsl L --usl U --target T \
    --controllable x1 x2 --outdir o/window
```

Read the generated markdown and look at every PNG before writing conclusions. Scripts are a starting point: write extra code (PLS, change-point, SHAP, DOE design, optimization) whenever the question needs it.

Worked lesson from testing: on pooled multi-grade data, a tag that only tracks grade (e.g., steam, speed) shows up as the "top correlation" and clustering simply rediscovers grades. The partial-correlation and within-group columns, plus the cluster×grade cross-tab, expose this — then rerun per grade with `--query`.

## When data isn't available yet

If the user only describes the problem, don't stall. Propose the analysis plan tailored to their process, list exactly which columns you need (Y with spec, X tags, timestamp/batch ID, grade, event logs), the recommended aggregation level, and offer to generate a synthetic example to demo the workflow.

## Domain context

For paper/board machines (quality variables, typical drivers, lags, grade effects), read `references/paper-machine.md`. For other processes, apply the same workflow and ask the user for the key physics.
