# Methods Reference

Contents
1. Distribution & normality
2. Capability & sigma
3. Correlation family
4. Group comparison
5. Dimensionality reduction (PCA / PLS)
6. Regression & ML models
7. Time-series specifics (lag, change-point, autocorrelation)
8. Clustering & regimes
9. Optimization & DOE
10. Common traps checklist

---

## 1. Distribution & normality

- Histogram bin width: Freedman–Diaconis (`2·IQR·n^(-1/3)`) is robust; overlay KDE.
- Normality: Anderson–Darling or Shapiro–Wilk (sample ≤5000). With big n, tests reject tiny deviations — trust a Q-Q plot more.
- Skewed Y (e.g., defects, dirt counts, porosity): try log / Box-Cox / Johnson transform before capability, or use percentile-based capability (ISO 22514: use 0.135% and 99.865% percentiles instead of ±3σ).
- Bimodal: fit a 2-component Gaussian Mixture; then find which variable (grade, crew, shift, supplier, speed band) separates the modes.

## 2. Capability & sigma

- σ_within = MR̄ / 1.128 (individuals) or R̄/d2 (subgroups). σ_overall = sample std.
- Cp = (USL−LSL)/(6σ_within); Cpk = min(USL−μ, μ−LSL)/(3σ_within). Pp, Ppk use σ_overall.
- One-sided spec: only Cpu or Cpl.
- Interpretation: Cpk < 1.0 not capable; 1.0–1.33 marginal; ≥1.33 capable; ≥1.67 for critical.
- Cp ≫ Cpk → centering problem (cheap fix: move the mean). Cp low → variation problem (need driver analysis). Pp ≪ Cp → drift / between-period shifts → look for change-points and regimes.
- Confidence interval on Cpk matters for small n (n<100 → wide). Report it.
- Sigma bands: expected fraction outside ±kσ for normal: 1σ 31.7%, 2σ 4.55%, 3σ 0.27%. Observed ≫ expected = special causes / heavy tails.
- Control chart rules (Western Electric): 1 point beyond 3σ; 2 of 3 beyond 2σ same side; 4 of 5 beyond 1σ same side; 8 in a row same side of center; 6 trending. Compute limits from a stable reference period, not the whole dataset if it contains shifts.

## 3. Correlation family

3.1 **Pearson** – linear, sensitive to outliers. **Spearman** – monotonic, rank-based. **Kendall** – robust for small n / ties.
3.2 **Non-linear**: mutual information (sklearn `mutual_info_regression`), distance correlation (catches U-shapes), maximal information coefficient. Also bin X into deciles and plot mean Y per bin — most intuitive for engineers.
3.3 **Partial correlation**: correlation of residuals of X~Z and Y~Z. Use to remove speed, grade, basis weight, or production rate effects. Or compute correlations *within* each grade and compare.
3.4 **Multicollinearity**: VIF > 5–10 means redundant. Cluster the correlation matrix (hierarchical, 1−|r| distance) and keep one representative per cluster, preferably the controllable one.
3.5 **Significance**: with n in thousands, almost every r is "significant". Focus on effect size and stability across time periods (compute r per month; is the sign consistent?).
3.6 **Multiple testing**: Benjamini–Hochberg FDR when screening many X.
3.7 **Correlation ≠ causation**: operators adjust X in response to Y (feedback loops, QCS control) — this creates correlations with the "wrong" sign. Controlled variables (e.g., basis weight under QCS control) show low correlation with their actuator even though the actuator is causal. Check the controller structure.

## 4. Group comparison

- Two groups (good vs. bad, before vs. after): Welch t-test or Mann–Whitney U; report effect size (Cohen's d, or Cliff's delta for non-parametric) and median difference in engineering units. KS test for distribution-shape differences.
- Many groups (grade, crew, supplier): one-way ANOVA or Kruskal–Wallis; post-hoc Tukey / Dunn. Report η² (how much of Y variance the grouping explains).
- Variance components (nested ANOVA): split total variance into e.g. between-grade / between-reel / within-reel / measurement. Tells you where to attack.
- Measurement system: if lab repeatability is a big fraction of spec width, the "gap" may be measurement noise. Suggest Gage R&R (%GRR < 10% good, >30% bad).

## 5. Dimensionality reduction

- **PCA** on standardized X: find groups of tags that move together; inspect loadings; plot scores colored by Y or in-spec flag. Hotelling T² and SPE (Q) for multivariate monitoring.
- **PLS regression** (X → Y): preferred over OLS when X are many and collinear (typical plant data). Use VIP scores (>1 important) and regression coefficients. Choose components by cross-validation (time-split).
- Always standardize (z-score) first; drop near-constant tags.

## 6. Regression & ML models

6.1 **OLS** with standardized X for relative importance; with raw units for engineering slopes. Check residuals vs time (autocorrelation → use HAC/Newey-West errors or aggregate).
6.2 **Lasso / Elastic Net** for variable selection among many X; check stability of selected set across bootstrap / time folds.
6.3 **Random Forest / Gradient Boosting**: captures thresholds and interactions. Use **permutation importance** (not impurity importance, which is biased toward high-cardinality variables), **partial dependence / ICE plots** to see shape and optimal ranges, **SHAP** (if available) for per-point explanations and interaction values.
6.4 Validation: TimeSeriesSplit or train on first 70% of time, test on last 30%. Report R², MAE in engineering units. If test R² ≪ train R², the model memorized regimes.
6.5 Logistic regression / classifier on in-spec flag when the question is "probability of being out of spec".
6.6 Don't extrapolate: recommendations only within the range covered by data.

## 7. Time-series specifics

- **Lag estimation**: cross-correlation of first-differenced (or detrended) X and Y over lags 0…L; peak lag = transport/response delay. Differencing avoids spurious peaks from shared trends. Shift X by the lag before any other analysis.
- **Autocorrelation**: ACF of Y; effective sample size n_eff ≈ n(1−ρ)/(1+ρ). Aggregate to reel/batch or hourly to reduce it.
- **Change-point detection**: CUSUM, PELT (`ruptures` library if installable), or rolling mean with a simple binary segmentation. For each change-point, list what else changed at the same time (X shifts, maintenance, raw material lot, crew).
- **Grade changes / transitions**: exclude a settling window after each change, or analyze transitions separately (transition time is itself an optimization target).
- **Seasonality**: shift pattern (8/12h), daily temperature, weekly raw material deliveries.

## 8. Clustering & regimes

- Purpose: discover distinct operating states, then compare quality between them. Cluster on **X only** (process state), then profile Y per cluster — otherwise you're just clustering on the answer.
- Preprocess: standardize; remove redundant tags (one per correlation cluster); optionally PCA to 3–8 components first.
- **k-means**: fast, spherical clusters; pick k by silhouette + elbow + interpretability (usually 3–6).
- **Gaussian Mixture**: elliptical clusters, soft membership; choose k by BIC.
- **DBSCAN / HDBSCAN**: arbitrary shapes, labels outliers as noise (useful for abnormal runs).
- **Hierarchical (Ward)**: dendrogram helps explain to engineers.
- Profile each cluster: size, time share, mean/median of key X, Y mean, σ, Cpk, % out-of-spec. The best cluster (high Cpk, reasonable throughput) defines a candidate operating window.
- Check clusters aren't just grades/time periods in disguise (cross-tab cluster × grade × month).

## 9. Optimization & DOE

- **Golden window from history**: select the top-performing runs (e.g., in-spec and |Y−target| in best quartile, and stable). Take the 10th–90th percentile of each key X in that subset as the window. Check how many historical points fall inside *all* windows simultaneously and their quality — multi-variable windows shrink fast.
- **Model-based**: fit a model (PLS/GBM), then optimize Y (or Cpk, or P(in-spec)) over controllable X within historical ranges using `scipy.optimize` or grid search; add constraints (other quality variables in spec, speed ≥ target, energy cost). Penalize distance from well-covered data.
- **Multi-objective**: show a Pareto trade-off (e.g., strength vs. refining energy vs. speed) rather than one "optimum".
- **Confirm with DOE**: 2^k or fractional factorial on top 2–5 controllable X with realistic step sizes; then Response Surface (Central Composite / Box-Behnken) near the optimum. Use EVOP (small deliberate changes during production) when big moves are unsafe.
- **Robust design**: prefer settings where Y is insensitive to uncontrollable noise (flat region of PDP), not just where mean is best.

## 10. Common traps checklist

- [ ] Mixed grades/products pooled → spurious correlations
- [ ] Downtime/startup/sheet breaks not removed
- [ ] Lag between X and Y ignored
- [ ] Random train/test split on time series
- [ ] Feedback control hiding true causal effect
- [ ] Operator reaction reversing the causal direction
- [ ] Reporting r without engineering-unit effect size
- [ ] Recommending settings outside historical range
- [ ] Measurement noise mistaken for process variation
- [ ] Only one method used; no triangulation
