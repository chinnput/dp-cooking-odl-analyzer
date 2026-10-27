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

*As of 2026-10-21.*

- **Branch:** `feat/press1-digester-exact-match`, pushed to GitHub (last pushed commit `4d9c5f9`). Not merged to `main`.
- **Digester batch analysis (new main work):** `Digester_Analysis/` — see its `README.md` (Thai, detailed)
  - `pull_data.py` pulls the digester/lab/status tags at 5 min (expanded from 99 to cover the alkali, steam % / temperature and heat-exchanger groups from `workflow.md`); `01_build_master.ipynb` builds `data/batch_master.csv` (1 row = 1 batch), `data/lab_linked.csv`, `data/phase_summary.csv` (1 row = 1 phase run) and `data/phase_summary_with_lab.csv` (same, with the batch's Press 1 lab values); `02_analysis.ipynb` reads only those CSV files.
  - `phase_summary.csv` (`batch.phase_summary`): one row per phase run with `start` / `end` / `minutes` and `mean` / `min` / `max` of every numeric sensor for that digester plus the shared sensors. Ids and phase timers (`batch_number`, `press1_status`, `*_time`) are left out (`config.PHASE_SUMMARY_SKIP`). It is the filtered raw table to pivot in Excel.
  - `phase_summary_with_lab.csv` (`batch.phase_summary_with_lab`): `phase_summary` plus the batch's Press 1 Kappa / Viscosity / Brightness (value + sample count, `config.PHASE_SUMMARY_LAB_FIELDS`) and the `kappa_grade` / `viscosity_grade` low/good/high labels. Lab is a property of the whole batch, so every phase run of that batch repeats the same lab value; a batch with no sample stays blank. Merged on `(digester, batch_id)` so it respects the AF lag (not a raw-timestamp join).
  - **Lab grade (`batch.add_lab_grades`):** `kappa_grade` and `viscosity_grade` label each batch `low` / `normal` / `high` against `config.QUALITY_TARGETS` (Kappa 9.0–9.5, Viscosity 725–775 — **provisional** bands, to confirm with the process team). `normal` = inside the band, inclusive; a batch with no lab sample stays NaN. `overall_grade` is `normal` only when every target is `normal`, else `abnormal` (NaN if any target has no sample). *Renamed 2026-10-27: good→normal, bad→abnormal.* Raw deviation is intentionally not stored — the user computes it from the raw lab values. Added to both `batch_master.csv` and `phase_summary_with_lab.csv`.
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
  - ~~The PI Status and Lab tags use `Step = 0`, so PI interpolates them linearly. AF Step 8 also writes fractional status values (`Pteam/Lag_Time_Sequence.md`, issue G). The fix is `PrevVal` in AF and/or `Step = 1` on the PI points.~~ **Fixed 2026-10-20:** AF Step 8 now uses `PrevVal()` instead of `InterpolatedValues()` for all `Bn_Discharge_FinalTime_Press1_Status` attributes (B1–B4). This eliminates fractional status values during downtime, resolving the spurious digester assignment spikes in the Press 1 analysis.
  - Notebook N counts interpolated points, not real lab samples. Kappa and Viscosity are sampled every 4 h and Brightness every 2 h.
  - Samples taken during downtime (production ≈ 0) are not yet excluded.
  - The MI Cube token is still in git history (`a7b9d17`, `eddf86a`) and should be rotated. Hard-coded tokens remain in `onedrive_to_pi/config.py`, the `test_*` scripts and the gateway default.
  - D4 temperature tag (`PM2.404TI423` vs `TI418`) behaves differently from D1–D3 — D4 H-factor is provisional until confirmed.
  - H-factor ignores the chip weight (temperature × time only). Chips per batch vary (SD 5–7 t) while the white liquor volume is almost fixed (median 12.86 m³ in every digester), so fewer chips = more alkali per ton at the same H. Added `white_liquor_m3` and `white_liquor_per_ton_chip`; per ton vs Kappa is negative in all 4 digesters (Spearman −0.12 to −0.19, weak). Next: ask whether WL is dosed by fixed volume or by chip weight; confirm `PM2.104FIC532`; get a usable chip moisture (`MI801` stuck at 35) for dry weight; EA vs AA → alkali charge % on wood; then look at Kappa vs H-factor + alkali charge together on Jun–Oct data.
  - D4 is a newer digester; its volume may differ from D1–D3 (to confirm). Chips per batch: D4 ≈ 72 t vs D1–D3 87–95 t; steam to heater D4 ≈ 20 vs 1–3. Size-dependent values (weight, flows, L:W) should not be compared across D4 and D1–D3 directly.
  - PI AF "4. LC Chest Outlet Flow" = `PM2.105FIC544` (PI descriptor: Press 3 Pulp Feed) + `PM2.105FIC238` (Press 1 Pulp Feed), with a 125 m³ chest (= LC Chest 2 size) — to confirm with the AF author.
  - Alkali tags `PM2.404AIC670/667` (g/l): EA or AA, and fresh WL or accumulator mix? To confirm.
  - `LP_pressure` (PIC102/202/302/402, bar) was added to `config.COOKING` + `BATCH_FEATURES` (`HEAT&COOK` mean) on 2026-10-27, but the current cache has no data for these tags, so `LP_pressure_mean_heat_and_cook` is all NaN until a PI re-pull. The exact meaning of PIC102 (vs PIC104 digester_pressure) is to confirm.

---

## Progress Log

### 2026-10-21 — Added steam_heater_temp, p factor, and a combined Kappa+Viscosity grade table

**What was done:**

- **config.py** — added `("steam_heater_temp", ["HEAT&COOK"], "max")` to `BATCH_FEATURES`. The `steam_heater_temp` tag (D1 `PM2.104TIC120:MV` … D4 `PM2.404TIC420:MV`) was already defined in the `cooking` pull category but was never summarised into the master, so `batch_master.csv` gained the column `steam_heater_temp_max_heat_and_cook`. `max` matches the workflow note that the MP-steam valve closes once the steam heater reaches ~164 °C.
- **02_analysis.ipynb `gradesum-code-01`** — fixed `PARAMS` names to match the real master columns (`pfactor_actual_last_prehydrolysis`, `pfactor_setpoint_last_prehydrolysis`; added `steam_heater_temp_max_heat_and_cook`). Raw sensor names like `steam_heater_temp` / `pfactor_actual` silently drop out because the cell filters with `if p in sub.columns`.
- **02_analysis.ipynb** — added a second table pair (`overallsum-md-01` / `overallsum-code-01`) after the per-target grade table. `overall_grade` = `good` only when Kappa *and* Viscosity are both `good`, else `bad`; if either lab grade is missing the batch is dropped (NaN). Same `median (Q1–Q3)` layout, one table per digester, columns `bad` / `good`. Kept as a separate table so the per-target one is untouched.

**Results:**

- Rebuilt `batch_master.csv` from the existing cache (no PI pull by me); `steam_heater_temp_max_heat_and_cook` is populated for 940/949 batches, D1–D3 ≈ 159–163 °C and D4 ≈ 164 °C — consistent with the 164 °C workflow note; D4 max 222.8 and D3 min 95.8 are start/trip outliers.
- `overall_grade` `good` counts are very small (D1 6, D2 4, D3 0, D4 4 on the provisional band) because both targets must land together — strictly a hypothesis. Notebook JSON parses (30 cells); all four tables render; no Pylance problems in the notebook or `config.py`.
- *Found by:* replicating the cell logic headless with the project `.venv` on `data/batch_master.csv`.

### 2026-10-21 — Moved overall_grade into the master as a permanent column

**What was done:**

- **batch.py `add_lab_grades`** — added an `overall_grade` column so the combined Kappa+Viscosity verdict lives in the pipeline instead of being recomputed in the notebook. Written as a general loop over `config.QUALITY_TARGETS`: it collects the per-target grade columns (`kappa_grade`, `viscosity_grade`, …), a batch is `good` only when every target grade is `good`, `bad` if any present grade is not `good`, and NaN if any target has no lab sample. Because it reads the targets from config it will pick up `brightness` automatically if a third target is added — no code change needed.
- **02_analysis.ipynb `overallsum-code-01`** — removed the five lines that recomputed `overall_grade` inside the notebook; the cell now reads `master["overall_grade"]` directly, so the notebook and the master can never disagree.

**Results:**

- Rebuilt `batch_master.csv` from the existing cache (no PI pull by me); the master now has 73 columns including `overall_grade`. Per-digester counts match the earlier headless check exactly — D1 good 6 / bad 67, D2 4 / 80, D3 0 / 73, D4 4 / 56 — and the notebook table renders the same `n` values from the master column. Notebook JSON parses (30 cells); no Pylance problems in `batch.py` or the notebook.
- *Found by:* rebuild + headless replay of the notebook cell with the project `.venv` on `data/batch_master.csv`.

### 2026-10-21 — Added a "process values by quality grade" table to 02_analysis

- Added a markdown + code cell (`gradesum-md-01` / `gradesum-code-01`) after the quality map. For each digester it splits batches by lab grade (`low` / `good` / `high`) and prints one table per digester: rows = process parameters, columns = the three grade groups, value = `median (Q1–Q3)`, plus an `n (batches)` row.

**What was done:** the cell exposes `GRADE_COL` (default `viscosity_grade`), `GRADE_ORDER`, and a `PARAMS` list (10 workflow X parameters — H-factor, white-liquor volume / per-ton, L:W, chip weight, cook temperature / pressure, steam to heater, accumulator alkali, black-liquor conductivity) so it is easy to re-point at `kappa_grade` or other sensors. Uses `median (Q1–Q3)` (not mean ± SD) because batch data is skewed and has outliers. Reads `master` (1 row = 1 batch), already filtered to `quality_flag == "ok"` in the setup cell. This is the first of a planned pair; a distribution (boxplot) cell will follow.

**Results:**

- Verified on the existing cache (no PI pull). Notebook JSON parses (28 cells); the four tables render. `good`-group sizes are small (viscosity_grade `good`: D1 26, D2 18, D3 12, D4 18), so the tables are a hypothesis, not a setpoint. Early read on this provisional window: in several digesters the `low` (soft pulp) group shows higher white-liquor volume (e.g. D1 14.5 vs 12.9 m³ at `good`/`high`) and higher accumulator alkali — consistent with over-cooking, but n is small and the bands are provisional.
- *Found by:* replicating the cell logic headless with the project `.venv` on `data/batch_master.csv`.

### 2026-10-21 — Added low/good/high lab quality grades to the batch and phase tables

- Added `batch.add_lab_grades(df)` and two config constants (`config.QUALITY_TARGETS`, `config.QUALITY_GRADE_NAMES`). New columns `kappa_grade` / `viscosity_grade` now appear in both `batch_master.csv` and `phase_summary_with_lab.csv`.

**What was done:** `config.py` holds the provisional target bands (`press1_kappa` 9.0–9.5, `press1_viscosity` 725–775) and the short grade names. `add_lab_grades` is vectorised (`np.where` → `low` / `good` / `high`, `good` inclusive of both limits) and NaN-safe (a batch with no lab value keeps NaN, not a string). `build_master` grades the single `lab_batch` frame once (`lab_batch = add_lab_grades(lab_per_batch(linked))`), so the grade flows into both the batch merge and the phase merge; `phase_summary_with_lab` selects the grade columns alongside `PHASE_SUMMARY_LAB_FIELDS`. Deviation columns were deliberately dropped — the user derives deviation/correlation from the raw lab values. Brightness is not graded yet (no confirmed band).

**Results:**

- Verified on the existing cache (no PI pull). Boundary unit check passes: Kappa 8.9→low, 9.0/9.2/9.5→good, 9.6→high, NaN→NaN; Viscosity 700→low, 725/775→good, 800→high. Grades landed in both files (`batch_master` + `phase_summary_with_lab.csv`, now 87 columns). Cross-check: 0 grade/value mismatches against the raw lab column. Distribution on this window (949 batches): `kappa_grade` NaN 652 / high 237 / good 44 / low 16; `viscosity_grade` NaN 654 / high 204 / good 75 / low 16 — skewed to `high` because the bands are provisional sample values, not yet the real targets.
- *Found by:* running `build_master` + a boundary unit test on `data/digester_2026-08-01_2026-10-01.csv.gz` with the project `.venv`.

### 2026-10-21 — Added a per-digester Kappa–Viscosity quality map to 02_analysis

- Added a markdown + code cell near the top of `02_analysis.ipynb` (after the setup cell, before Phase 1): a 2×2 scatter, one digester per panel, Kappa (x) vs Viscosity (y), from `master` (1 point = 1 batch).

**What was done:** the cell exposes `X_COL` / `Y_COL` / `SIGMA` at the top so any lab pair can be plotted, plus an unused `CLUSTER_K` hook reserved for future k-means colouring. A small `within_sigma` helper trims outliers per digester on both axes (default ±2σ). Uses `master`, not `phase_summary_with_lab`, because lab is one value per batch — the phase table repeats it across phase runs, which would overcount points in a scatter.

**Results:**

- Verified on the existing cache (no PI pull), batches with `quality_flag == "ok"` and a lab value: D1 73→67 (−6), D2 84→75 (−9), D3 73→67 (−6), D4 60→55 (−5) after the ±2σ trim. No errors; notebook JSON parses (26 cells).
- *Found by:* running the cell logic headless with the project `.venv` on `data/batch_master.csv`.

### 2026-10-21 — Merged Press 1 lab quality into the phase summary

- Added `batch.phase_summary_with_lab(phases_summary, lab_batch)` and a new output `data/phase_summary_with_lab.csv`. `phase_summary.csv` is left unchanged.

**What was done:** `config.py` gained `PHASE_SUMMARY_LAB_FILE` and `PHASE_SUMMARY_LAB_FIELDS` (Press 1 Kappa / Viscosity / Brightness value + `_samples`, derived from `LOG_BOOK_LAB_COLUMNS`). `build_master` now keeps the `lab_per_batch` result in a single `lab_batch` variable and reuses it for both the batch-level merge and the phase-level merge (no second computation). The merge is on `(digester, batch_id)` `how="left"`, so it reuses the same AF-lagged batch link as `batch_master` — **not** a raw-timestamp join (lab is measured at Press 1 after the lag, so a timestamp join would mislabel it). `save_outputs` / `load_phase_summary(with_lab=True)` and `01_build_master.ipynb` were wired to the new file.

**Why a batch-level merge:** lab is one value per batch measured downstream at Press 1, not per phase. Repeating the batch value across that batch's phase runs keeps the filtered-raw table pivotable by phase while carrying the quality Y, and avoids inventing per-phase lab numbers that do not exist.

**Results:**

- Verified on the existing cache (no PI pull): 6323 phase runs × 85 columns (79 + 6 lab columns). 1982 / 6323 phase runs (31.3%) carry a `press1_kappa` value; the rest are blank (batches with no lab sample, kept as NaN). The lab value in `phase_summary_with_lab` matches `batch_master` for every batch (0 mismatches). Saved and reloaded `phase_summary_with_lab.csv` cleanly.
- *Found by:* running `build_master` on `data/digester_2026-08-01_2026-10-01.csv.gz` with the project `.venv`.

### 2026-10-21 — Added workflow tags and a phase-level summary table

- Added the PI tag groups that `workflow.md` highlights but were not pulled: alkali concentration, LP/MP steam valve % and steam-heater temperature, the heat-exchanger group, chip moisture (`MI801`). They are registered in `config.py`; the data cache still holds the old tags until the next pull.
- Added `batch.phase_summary(df, phases)` and wired it through `build_master`, `save_outputs` / `load_phase_summary` and `01_build_master.ipynb`.

**What was done:** `config.py` gained the new per-digester cooking tags (`pfactor_temp`, `steam_heater_temp`, LP/MP steam valves) and three shared groups (`ALKALI_SHARED`, `HEAT_EXCHANGER_SHARED`, `MOISTURE_SHARED`), plus `PHASE_SUMMARY_*` constants, a `text_columns()` helper and a `PHASE_SUMMARY_SKIP` list. `phase_summary` takes each phase run, slices the sensor data to its window and records `mean` / `min` / `max` for that digester's own tags and the shared tags only (other digesters' columns, ids and phase timers are left out, prefixes stripped for readable names).

**Results:**

- Verified on the existing cache (no PI pull): 6323 phase runs × 79 columns (7 meta + 24 sensors × 3 stats). Values match `batch_master` (e.g. D1 HEAT&COOK `circulation_temp` max 156.21). Saved and reloaded `phase_summary.csv` cleanly, with `start` / `end` as datetimes.
- The table is the "filtered raw data" the user asked for: one row per sequence run, start-to-end with its averages, ready to pivot in Excel.
- *Found by:* running `build_master` on `data/digester_2026-08-01_2026-10-01.csv.gz` with the project `.venv`.

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

  |            | D2                  | D3                             | D4                                |
  | ---------- | ------------------- | ------------------------------ | --------------------------------- |
  | Kappa      | +0.31 [0.00, +0.62] | **+0.51** [+0.24, +0.79] | **+0.50** [+0.09, +0.87]    |
  | Brightness | **−0.41**    | **−0.43**               | **−0.79** [−1.22, −0.31] |

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

|                  | Mean  | Median | SD   | ±2σ        | % in SOP |
| ---------------- | ----- | ------ | ---- | ------------ | -------- |
| Kappa (all)      | 10.27 | 10.31  | 0.80 | 8.66–11.88  | 1.5%     |
| Viscosity (all)  | 791.9 | 795.6  | 42.0 | 707.8–876.0 | 1.9%     |
| Brightness (all) | 35.86 | 35.60  | 1.59 | 32.67–39.04 | 16.7%    |

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

### 2026-10-20 — AF Step 8 fix: `PrevVal()` replaces `InterpolatedValues()` for Press 1 digester status

- Diagnosed spurious digester-assignment spikes during downtime: AF Step 8 used `InterpolatedValues()`, which caused PI to linearly interpolate binary status (0/1, 0/2, 0/3, 0/4) into fractional values (0.5, 1.2, 2.8, etc.)
- Updated AF element `PPPC_DP_Cooking` Step 8 expression for all four digesters (B1–B4): replaced `FirstValue(InterpolatedValues(...))` with `PrevVal('Bn_DischargeStatus_FinalTime_Status_Rev', LCChest_RetentionTime)` to read the last stable status value before the lag window
- This ensures the Press 1 digester assignment is always an integer (1, 2, 3, 4, or 0 for no pulp), not a fractional spike

**What was done:** Updated the PI AF analysis Step 8 formula in the `PPPC_DP_Cooking` element; applied the same fix to all four digester Press1_Status attributes.

**Results:**

- Press 1 digester-assignment plot (after this change) shows clean horizontal bands per digester instead of fractional spikes during downtime.
- Notebook digester assignment now correctly filters to integer status values, eliminating the need for post-hoc rounding.
- *Found by:* visual inspection of the realtime_pi_press1_analysis.ipynb plots showing frequent blue (undefined digester) bands correlated with downtime windows.

### 2026-10-27 — Renamed quality grades good/bad -> normal/abnormal; added LP_pressure tag

**What was done:**

- **Grade terminology** — changed the quality labels from `good`/`bad` to `normal`/`abnormal` across the pipeline and notebook, to match the Normal/Abnormal language used in the Pteam clustering work.
  - **batch.py `add_lab_grades`** — per-target grade now returns `low` / `normal` / `high` (was `low` / `good` / `high`); `overall_grade` now returns `normal` / `abnormal` (was `good` / `bad`). Logic unchanged: a batch is `normal` only when every present target grade is `normal`, `abnormal` if any is off, NaN if any target has no lab sample.
  - **02_analysis.ipynb** — updated 4 cells (`gradesum-md-01`, `gradesum-code-01`, `overallsum-md-01`, `overallsum-code-01`): `GRADE_ORDER = ["low", "normal", "high"]`, `OVERALL_ORDER = ["abnormal", "normal"]`, plus the markdown text, docstrings and print labels.
- **config.py** — added a new per-digester pressure group `LP_pressure` to `COOKING` (D1 `PM2.104PIC102:MV`, D2 `PM2.104PIC202:MV`, D3 `PM2.104PIC302:MV`, D4 `PM2.404PIC402:MV`, bar) and `("LP_pressure", ["HEAT&COOK"], "mean")` to `BATCH_FEATURES`, giving the column `LP_pressure_mean_heat_and_cook`. This is a different tag from `digester_pressure` (PIC104).

**Results:**

- Rebuilt `batch_master.csv` from the existing cache (no PI pull by me): 1540 batches x 75 columns. `overall_grade` -> `{normal, abnormal}`, `kappa_grade` / `viscosity_grade` -> `{low, normal, high}`.
- `LP_pressure_mean_heat_and_cook` exists but is all NaN (count 0 in every digester) — the cache has no PIC102/202/302/402 data yet. Needs a PI re-pull (done by the user) before the column carries values.
- Notebook grade cells (5, 7) run headless with the new labels; no Pylance problems in `batch.py`, `config.py` or the notebook.
- *Found by:* headless rebuild + value-set check on the saved master, and a headless exec of the two grade cells.
