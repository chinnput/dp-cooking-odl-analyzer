# DP Cooking ODL Analyzer

## Project Overview

The project analyzes and reduces process variation in **DP Cooking (Digesters D1–D4)** and the **ODL (Oxygen Delignification) washing stage** of **Pulp Line 2**.

- **Goal of the current phase:** "Just Visualize, Not Optimize." Build reliable data pipelines and show process variation clearly before proposing process changes.
- **Quality outputs (Y):** Press 1 lab Kappa, Viscosity and Brightness (`PULP-LINE2-*-PRESS1`).
- **Process inputs (X):** White Liquor flow, MP Steam flow, Production ODL, Press 1 feed consistency, Deknotting feed flow (DCS tags from PI).
- **Key question:** Which digester's pulp is at Press 1 at a given time, and does quality differ by digester?
- **Data path:**
  - Lab log book (SharePoint/OneDrive Excel) → `onedrive_to_pi` → PI tags (`write_old` gateway)
  - PI Server `VPKGDRBPPI01` → MI Cube API → `Lab_Analysis/realtime_pi_press1_analysis.ipynb`
  - Digester-to-Press 1 mapping: PI AF analysis in element `PPPC_DP_Cooking`. It writes the tags `Bk_Discharge_FinalTime_Press1_Status` (value k or 0), which are documented in `Pteam/Lag_Time_Sequence.md`.

---

## Current State

*As of 2026-10-15.*

- **Branch:** `feat/press1-digester-exact-match`, pushed to GitHub (last pushed commit `4d9c5f9`). Not merged to `main`.
- **Digester batch analysis (new main work):** `Digester_Analysis/` — see its `README.md` (Thai, detailed)
  - `pull_data.py` pulls 99 digester/lab/status tags at 5 min; `01_build_master.ipynb` builds `data/batch_master.csv` (1 row = 1 batch) and `data/lab_linked.csv`; `02_analysis.ipynb` reads only those CSV files.
  - H-factor = HOT LIQUOR FILLING + HEAT&COOK + DISPLACEMENT (`config.H_FACTOR_PHASES`); per-phase H kept for comparison.
  - Lab = real log-book samples only, linked to the batch through the (AF-lagged) Press 1 status.
  - Batches are flagged (`quality_flag`), not removed.
- **Press 1 overview notebook:** `Lab_Analysis/realtime_pi_press1_analysis.ipynb` (still uses PI-interpolated lab values and same-time sensor pairing — use for overview only)
  - Range 2026-08-01 → 2026-10-01, `INTERVAL = "15m"`, interpolated values from the MI Cube API.
  - **Digester assignment:** a row belongs to Dk only if `Bk == k` exactly and no other digester matches. Otherwise the row is NaN.
  - **Summary tables** (Mean, Median, SD, ±2σ, SOP, % in SOP) follow each Kappa, Viscosity and Brightness histogram.
  - **Spike filters:** Viscosity 400–2000, Brightness 25–50.
  - **Token:** the MI Cube token is read from `.env` (`MI_CUBE_API_TOKEN`). `.env` is git-ignored, and `.env.example` is committed.
- **Folder layout:** the original batch-clustering work (scripts, Excel outputs, `summary.md`, `Lag_Time_Sequence.md`) was moved into `Pteam/`. Git shows the moves as deletions plus untracked files until they are committed.
- **`onedrive_to_pi` pipeline:** production-ready. It writes 19 lab tags to PI and includes the October fixes for SharePoint download and log-book selection.
- **Open issues**
  - The SOP limits used in the notebook (Kappa 7.5–8.5, Viscosity 680–710, Brightness 37–40) put almost all data out of spec. They need confirmation from the process team.
  - The PI Status and Lab tags use `Step = 0`, so PI interpolates them linearly. AF Step 8 also writes fractional status values (`Pteam/Lag_Time_Sequence.md`, issue G). The fix is `PrevVal` in AF and/or `Step = 1` on the PI points.
  - Notebook N counts interpolated points, not real lab samples. Kappa and Viscosity are sampled every 4 h and Brightness every 2 h.
  - Samples taken during downtime (production ≈ 0) are not yet excluded.
  - The MI Cube token is still in git history (`a7b9d17`, `eddf86a`) and should be rotated. Hard-coded tokens remain in `onedrive_to_pi/config.py`, the `test_*` scripts and the gateway default.
  - D4 temperature tag (`PM2.404TI423` vs `TI418`) behaves differently from D1–D3 — D4 H-factor is provisional until confirmed.
  - H-factor ignores the chip weight (temperature × time only). Chips per batch vary (SD 5–7 t) while the white liquor volume is almost fixed (median 12.86 m³ in every digester), so fewer chips = more alkali per ton at the same H. Added `white_liquor_m3` and `white_liquor_per_ton_chip`; per ton vs Kappa is negative in all 4 digesters (Spearman −0.12 to −0.19, weak). Next: ask whether WL is dosed by fixed volume or by chip weight; confirm `PM2.104FIC532`; get a usable chip moisture (`MI801` stuck at 35) for dry weight; EA vs AA → alkali charge % on wood; then look at Kappa vs H-factor + alkali charge together on Jun–Oct data.
  - D4 is a newer digester; its volume may differ from D1–D3 (to confirm). Chips per batch: D4 ≈ 72 t vs D1–D3 87–95 t; steam to heater D4 ≈ 20 vs 1–3. Size-dependent values (weight, flows, L:W) should not be compared across D4 and D1–D3 directly.
  - PI AF "4. LC Chest Outlet Flow" = `PM2.105FIC544` (PI descriptor: Press 3 Pulp Feed) + `PM2.105FIC238` (Press 1 Pulp Feed), with a 125 m³ chest (= LC Chest 2 size) — to confirm with the AF author.
  - Alkali tags `PM2.404AIC670/667` (g/l): EA or AA, and fresh WL or accumulator mix? To confirm.

---

## Progress Log

### 2026-05-26 — Batch signatures and Normal/Abnormal clustering
- Cleaned the raw DCS data and extracted 900 batch signatures
- PCA + unsupervised clustering flagged 45 abnormal batches (top 5% by distance)
- Generated 25 Normal-vs-Abnormal boxplots

**What was done:** Status columns and sensor errors were cleaned (converted to NaN). Each digester batch was summarized into a feature vector and clustered to find batches that behave unlike the rest.

**Results:**
- Abnormal batches are process slowdowns, not small drifts.
- Deknotting feed flow (−43%), screening accept flow (−40%), Production ODL (−38%), O2 at Mixer 1 (−34%) and Press 1 consistency (−33%) all drop together.
- *Found by:* comparing Normal vs Abnormal cluster distributions (boxplots).

### 2026-06-05 — SOP violation tracking and digester heatmap
- `main_analysis.py` counts how many parameters each batch has outside the 5th–95th percentile "SOP" limits
- Identified the worst batch per parameter and built a D1–D4 heatmap
- `integrity_check.py` confirmed the reports match the raw signatures

**What was done:** The SOP limits were derived from the Normal cluster only. Each batch was then checked against those limits.

**Results:**
- Some batches have up to 89% of parameters outside the window.
- *Found by:* the SOP violation count per batch.

### 2026-06-10 — Digester performance comparison
- Built side-by-side boxplots for 27 parameters: batch mean (left) and within-batch SD (right) per digester
- Exported `digester_batch_performance_summary.xlsx`

**Results:**
- **D3** is the most stable with the highest production (284 ADT/D).
- **D1** has the largest batch-to-batch variation (production SD 47 ADT/D), including trips to zero.
- **D2** has the highest within-batch instability.
- **D4** has the highest SOP violation rate (23.4%) from drift on both sides of the limits.
- *Found by:* the batch-mean and within-batch SD boxplots, plus violation rates per digester.

### 2026-06-16 — Extended batch window to Press 1
- Redefined each batch window from Discharge start to the end of Press 1 washing (30,529 rows → 1,168 batches)
- Re-ran clustering: 59 abnormal batches

**Results:**
- The D2 abnormal rate fell to 5.37% and the D4 rate rose to 7.14% once the full wash cycle was included.
- *Found by:* re-running the clustering on the extended windows.

### 2026-07-07 — Specific steam and chemical consumption
- Added per-ton consumption: steam (t/ADT), White Liquor (m³/ADT), O2 Mixer 1 and O2 Pulp Heater (kg/ADT)
- Built boxplots, bell curves and a 1/x explanatory chart

**Results:**
- During abnormal batches, specific consumption spikes: O2 Pulp Heater +3,693%, steam +3,165%, White Liquor +616%, O2 Mixer 1 +486%. Production drops while feeds keep running.
- During upsets, White Liquor reaches 1.86 m³/ADT on D4 versus 0.48 on D2. D2's interlock cuts feeds back much better.
- *Found by:* Normal vs Abnormal comparison of the specific-consumption features, and the 1/x scatter.

### 2026-08-25 — Project handover
- New owner: Chinnput
- Scope narrowed to Line 2 with the "Just Visualize, Not Optimize" approach
- Plan: push lab Kappa/Viscosity/Brightness from SharePoint to PI, match lab times to batches, and add monthly D4 variation tracking

### 2026-08-27 → 2026-09-03 — `onedrive_to_pi` pipeline (commits `729c9ef` … `6004351`)
- Playwright SharePoint download, Excel parsing, time matching and a PI `write_old` client
- Local FastAPI gateway (`PI_gateway_for_write_old_data`)
- 6 new tags (pH and Brightness D1/D2), `new_tags_only` mode and a continuous loop
- 3-day lookback to catch backfilled lab entries

**Results:**
- 19 lab tags are written to PI at their exact sample timestamps.
- *Found by:* dry-run payloads and `test_read_interpolated.py` read-back.

### 2026-09-07 07:50 — Press 1 real-time analysis notebook (commit `a7b9d17`)
- Created `realtime_pi_press1_analysis.ipynb`, which reads 12 tags from PI via the MI Cube API (1-hour interpolated)
- KDE bell curves, boxplots, SD/CV%, SOP heatmap, mean/median heatmaps and per-digester correlation matrices

**Results (recorded at the time):**
- On D4, Production ODL vs specific steam has r = −0.75.
- MP steam vs Press 1 Kappa (r = −0.49), Viscosity (−0.34) and Brightness (+0.62).
- *Found by:* per-digester Pearson correlation on hourly data.
- *Note (2026-09-29):* this used linearly interpolated hourly data with a `> 0` digester rule. It was not adjusted for production or lag, so treat it as a hypothesis.

### 2026-09-23 — Lag-time sequence mapping (`Pteam/Lag_Time_Sequence.md`)
- Documented the 9-step PI AF logic that maps discharge-tank FIFO status plus LC chest retention (125 m³ ÷ flow + 5 min) to the Press 1 status of each digester
- Listed 9 issues (A–I) to fix in AF

**Results:**
- Issue G: AF Step 8 uses `InterpolatedValues`, so the status tags themselves can be fractional (0.5, 0.25, 3.2187).
- Issue I: hours with no active digester were counted as D1.
- *Found by:* reviewing each AF expression.

### 2026-09-29 — Data-quality diagnosis and digester comparison on real lab samples
- Reviewed the `process-gap-analysis` skill (`skillsAI/`) and extracted it for editing
- Pulled the status and lab tags at 1-minute resolution to see what PI actually stores
- Rebuilt the digester status as a step from PI recorded points
- Compared digesters using only real lab samples, with a batch-block bootstrap and adjustment for production, White Liquor per ton and Deknotting flow

**What was done:** Pulling 1-minute data showed straight-line ramps between recorded points. Recorded points were recovered by detecting where the slope changes. These were used to build the digester status and real lab sample times for Jul 1 – Sep 16. The notebook was temporarily rebuilt on this basis and later returned to the simpler hourly approach at the user's request. The findings below came from that analysis.

**Results:**
- **PI interpolates the Status and Lab tags linearly** (`Step = 0`). This creates values such as 0.018 and 1.81.
  - *Found by:* 1-minute pulls, where every minute had a different value.
- **Lab sampling:** Kappa and Viscosity are measured every 4 h (≈305 and 333 samples) and Brightness every 2 h (≈623). The hourly notebook therefore had 2–4× more points than real samples.
  - *Found by:* slope-change detection on the lab tags.
- **The old `> 0` rule over-counted D1:** 56% of hourly rows went to D1 versus a true time share of 26.5% (D2 25.0%, D3 27.6%, D4 14.0%, none 6.7%).
  - *Found by:* comparing the rule against the rebuilt step status.
- **D1 gives the best-delignified pulp.** Differences vs D1, adjusted, with 95% CI:

  | | D2 | D3 | D4 |
  |---|---|---|---|
  | Kappa | +0.31 [0.00, +0.62] | **+0.51** [+0.24, +0.79] | **+0.50** [+0.09, +0.87] |
  | Brightness | **−0.41** | **−0.43** | **−0.79** [−1.22, −0.31] |

  Viscosity shows no significant difference. The gap remains after adjusting for the ODL-side tags, which points to cooking conditions in the digesters.
  - *Found by:* OLS with digester dummies and covariates, batch-block bootstrap (1,000 resamples), Kruskal-Wallis and a monthly consistency check.
- **The quality gap is line-wide, not digester-specific:** Kappa ≈ 10.2 (SOP 7.5–8.5), Viscosity ≈ 790 (680–710) and Brightness ≈ 36 (37–40) are all out of spec in the same direction (under-delignified).
  - *Found by:* the SOP diagnostic table. The SOP values themselves still need confirmation.

### 2026-10-02 — `onedrive_to_pi` fixes (see `onedrive_to_pi/summary.md`)
- step0: unique temp file plus retry when the target is locked, visible SSO/MFA login with up to 5 min wait, UTF-8 stdout
- step1: choose the log book by (year, month) parsed from the filename, handle `9.` vs `09.`, ignore quarantine copies, fix year parsing (`…2025 in JAN 2026`)

**Results:**
- Data had stopped updating after 2026-09-24 because step1 picked the newest-mtime file, which could be the wrong month.
  - *Found by:* tracing which Excel file each run selected.

### 2026-10-06 15:15 — Exact-match digester rule (commit `eddf86a`)
- `get_active_digester`: Dk only when `Bk == k` exactly. No match or more than one match → NaN
- Tried a minute-level "Digester Rule v1" (carry-forward ≤ 4 h, ≥ 80% per hour), then reverted it to keep the notebook simple
- Fixed the boxplot dtype error (float `1.0` vs `order=[1, 2, 3, 4]`)
- Moved the MI Cube token from the notebook to `.env`

**Results:**
- **September 2026, hourly:**
  - 82.9% of hours match exactly one digester, and all 577 of 577 are correct against recorded status.
  - 17.1% are NaN: 89 hours have a value at 90–99% of k (for example B2 = 1.95, all correct digesters), 6 have every tag at 0, and 24 are ambiguous.
  - NaN share: July 30.4%, August 25.5%.
  - *Found by:* comparing the hourly rule with the 1-minute recorded step status.
- About 20% of PI recorded status points are fractional (B1 499/2,956, B2 697/3,422, B3 693/3,323, B4 414/1,852). This confirms AF issue G.
  - *Found by:* validating Rule v1, where carried-forward minutes agreed with the recorded status only 42% of the time.
- Decision: keep the exact-match rule and accept losing about 17% of rows rather than mislabelling them.

### 2026-10-09 — Summary tables and Brightness spike filter
- Added `quality_summary_table()` and tables after each histogram: N, Mean, Median, SD, −2σ, +2σ, SOP Low/High, % in SOP
- Added the 25–50 filter to the Brightness histogram and table

**Results:**

| | Mean | Median | SD | ±2σ | % in SOP |
|---|---|---|---|---|---|
| Kappa (all) | 10.27 | 10.31 | 0.80 | 8.66–11.88 | 1.5% |
| Viscosity (all) | 791.9 | 795.6 | 42.0 | 707.8–876.0 | 1.9% |
| Brightness (all) | 35.86 | 35.60 | 1.59 | 32.67–39.04 | 16.7% |

- The ±2σ band of Kappa and Viscosity barely overlaps the SOP band.
- Without the spike filter, Brightness had SD 15–22 and a negative −2σ, so the old histogram legend values were wrong. The filter removed about 2.4% of points.
- *Found by:* the new summary tables, run on the notebook's data range and interval at that time.

### 2026-10-12 08:06 — Commit of accumulated work (commit `601dbdd`)
- Committed the notebook tables, `.env` handling, `onedrive_to_pi` fixes, gateway with 2 workers, the lag-time docs and `skillsAI/`
- `.gitignore` now covers `.env`, `*.tmp`, `*.log` and `Lab_Analysis/data/`
- Excluded a lab log sheet `.xlsx.tmp` and `debug.log` from git

### 2026-10-12 → 2026-10-14 — Digester tags found, `Digester_Analysis` structure (commits `f05336a`, `4d9c5f9`)
- Found the batch digester tags (area `PM2.104` for D1–D3, `PM2.404` for D4) via the PI AF element and a PI point search; listed in `batch_digester_tags.csv` and `batch_digester_tags_per_digester.csv`
- "DP" here is prehydrolysis kraft (Dissolving Pulp): each digester has P-factor tags and a PREHYDRAU phase
- No H-factor tag exists for Line 2 (only Line 1 `PM1.204H_FACTOR_CTRL`), so H-factor is calculated from the circulation temperature
- Built `Digester_Analysis/` (config by category, `pull_data.py`, batch/phase split from `MAINSEQ`, H-factor, real lab samples from the log book linked to batches)

**Results:**
- LC chest lag (AF formula, Aug–Sep): median 26 min retention + 5 min = ~31 min; flow ≤ 0 (lag forced to 5 min) 2.8% of the time.
  - *Found by:* recomputing the AF formula from `FIC544` + `FIC238`.

### 2026-10-15 — H-factor window check, clean `Digester_Analysis`, batch features
- Checked where the cooking happens: temperature profiles with phase bands and H-factor per phase
- H-factor window changed from HEAT&COOK only to HOT LIQUOR FILLING + HEAT&COOK + DISPLACEMENT; H is now calculated once over the timeline (the first version lost the first step of every phase, ~14% of HEAT&COOK)
- Clean structure: `build_master.py` (one function), `01_build_master.ipynb` (build + checks), `02_analysis.ipynb` (reads CSV, follows `workflow.md`), old notebook moved to `archive/`
- Batch features defined in `config.BATCH_FEATURES` (sensor, phase, statistic); added L:W ratio (approx.), P-factor gap, `quality_flag`
- Detailed Thai README written for `Digester_Analysis/`
- `Digester_Analysis` made standalone: own log book reader `logbook.py` (read only, folder in `config.LOG_BOOK_DIR`); no code imported from `onedrive_to_pi` any more
  - The new reader matches the old one 100% on shared sample times and recovers 2 days the old one skipped (2026-01-23, 2026-04-21: sheets narrower than column AD were dropped by `onedrive_to_pi` step 1)
  - *Found by:* comparing both readers' output sample by sample

**Results (Aug–Sep 2026):**
- Cooking already happens in HOT LIQUOR FILLING (liquor 130–165 °C) and DISPLACEMENT (~157 °C): HEAT&COOK is only 31% (D1), 50% (D2), 57% (D3) of the H-factor.
  - *Found by:* H-factor split per phase and temperature plots in `01_build_master.ipynb`.
- Circulation temperature is not valid in PREHYDRAU (pressure 7–9 bar but temperature ~85 °C, no circulation).
  - *Found by:* the same temperature plots.
- D4 `TI423` gives a large H during PREHYDRAU (median 577) unlike D1–D3 → D4 tag to verify.
- 949 batches; 904 `ok`, 27 `long_batch`, 11 `missing_phase`, 8 `unknown_phase` (one batch has two flags); 297 batches have a Kappa value (lab samples every 4 h).
- H-factor (new and HEAT&COOK-only) shows **no relationship** with Press 1 Kappa within each digester (Spearman ≈ 0).
  - *Found by:* scatter, 5 H-factor groups and good-vs-bad comparison per digester.
- P-factor reached is positively related to Kappa in D1–D3 (D2 Spearman +0.34, p < 0.01) — the strongest repeated signal so far; plausible for prehydrolysis kraft but not yet confirmed (time trend not yet removed).
- Accumulator alkali concentration is positively related to Kappa (D1 +0.31, D2 +0.30) — unexpected; tag meaning to confirm.
  - *Found by:* Spearman correlation of batch features vs Kappa per digester (`02_analysis.ipynb`).
