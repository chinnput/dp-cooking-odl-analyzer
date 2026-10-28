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

*As of 2026-10-27.*

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
  - **Per-digester surrogate check (2026-10-27):** per-digester models do not beat pooled; Kappa out-of-time R² < 0 in every set-up (Kappa is dominated by slow day-to-month drift the batch features don't capture). Viscosity drivers have the same sign in all 4 digesters. Steam flow tags are unreliable (D1–D3 negative zero offset, D4 pegged at 21). See the Progress Log entry of the same date.
  - **Viscosity surrogate (2026-10-27, focus now):** best out-of-time R² 0.11 (GBM pooled) — gate (0.30) not passed. Main driver `alkali_accumulator1_conc` (`PM2.404AIC670`, shared tag), ≈ −16 Viscosity per g/l, partly slow monthly drift. Pooled > partial pooling > per digester. Next: confirm AIC670 meaning/controllability, longer data (from Jan), alkali charge per ton.
  - **Prehydrolysis speed (2026-10-27):** P-factor rate / P-temp drive Viscosity more than prehydrolysis time or P-factor amount (within-week ρ −0.20 vs −0.01). P-temp SP 162 → 809, 163 → 780, 164 °C → 772 Viscosity (partly season). Hot vs cool at same PF setpoint −6 Visc, Kappa unchanged. Ridge with these features R² 0.21 (best, gate 0.30 not passed). Code: `XGboost_Model/`.
  - ~~`LP_pressure` all NaN~~ now populated in the cache and master (1529/1540, checked 2026-10-27). Original note: `LP_pressure` (PIC102/202/302/402, bar) was added to `config.COOKING` + `BATCH_FEATURES` (`HEAT&COOK` mean) on 2026-10-27, but the current cache has no data for these tags, so `LP_pressure_mean_heat_and_cook` is all NaN until a PI re-pull. The exact meaning of PIC102 (vs PIC104 digester_pressure) is to confirm.

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

### 2026-10-27 — Per-digester model check, Kappa noise ceiling, steam tag audit

**What was done:**

- Tested whether training one model per digester (D1–D4) beats a pooled model for the Desirability surrogate. Local files only (`Digester_Analysis/data/batch_master.csv`, `lab_samples.csv`, 5-min cache); no PI access. Validation = `TimeSeriesSplit(4)` (out-of-time R²), GradientBoosting depth 2 (xgboost not installed) + Ridge, 9 batch features (H-factor, P-factor actual, WL m³ and per ton chip, chip weight, L:W, heat&cook minutes, circulation temp, alkali conc 1).
- Noise ceiling on the raw lab log (Jan–Oct 2026): lag autocorrelation, short-term σ from consecutive diffs, variance between days / weeks / months.
- Per-digester good-vs-rest (good = Kappa ≤ 9.8 and Viscosity 700–800) with Mann-Whitney + within-digester Spearman.
- Audit of the steam tags in the 5-min cache during HEAT&COOK.
- Scripts were throwaway (session scratchpad), not added to the repo.

**Results:**

- **Data per digester is small:** batches with a Kappa result D1 111, D2 125, D3 129, D4 85 (median 1 real lab sample per batch).
- **Digesters differ in level:** Kappa D1 10.0 vs D2–D4 ≈ 10.4 (Kruskal p = 0.001); Viscosity not clearly different (p = 0.09). Setpoints differ too: H-factor D1 511 / D2 330 / D3 302 / D4 398; chip weight D4 72 t vs 86–93 t, so WL per ton chip is highest in D4 (0.187).
- **Per-digester models do not help.** Out-of-time R²: Kappa pooled −0.19 (GBM) / −0.11 (Ridge), per digester −0.42 to −0.10; Viscosity pooled 0.04 / 0.15, per digester −0.15 to 0.23 (the 0.23 is D4, n = 85, not reliable). Adding `Digester_ID` to the pooled model changes nothing. Random-split R² from Step 0 was optimistic.
- **Kappa is a slow-drift signal, not batch noise:** lag-1 autocorr 0.62 (4 h), lag-6 0.41; 59% of variance is between days, 31% between months. Monthly mean drifts up from 8.7 (Jan) to 10.5 (Sep). Short-term σ 0.59 vs total 0.96. Batch-level setpoints have ~0 within-digester correlation with Kappa (mean Spearman ≈ 0), so the drift comes from something the batch features do not capture (wood/chip quality, liquor strength, blending in the discharge tank).
- **Viscosity has consistent drivers in all 4 digesters** (same sign in each one): alkali accumulator 1 conc ρ −0.34 to −0.55, heat&cook minutes −0.24 to −0.45, WL m³ −0.20 to −0.34, P-factor −0.15 to −0.40. Same sign everywhere suggests a common response (setpoint difference, not a different digester response) → a pooled Viscosity model is the right shape.
- **Strict target hits are rare:** Kappa 9.0–9.5 and Viscosity 700–800 in 15 / 11 / 10 / 9 batches (D1–D4). Good-vs-rest differences are mostly not significant (only D1 chip weight p = 0.017 and alkali conc p = 0.027), so no per-digester operating window is supported yet.
- **Steam tag audit (HEAT&COOK, 5-min cache):**
  - `steam_to_heater_flow` D1–D3 is negative 52% / 85% / 93% of the time (resting value ≈ −5.7 / −2 / −3 t/h) → zero offset on the transmitter; phase means are biased.
  - `steam_to_heater_flow` D4 sits at 21.0 from P10 to P99 → pegged at range max (or wrong tag). Unusable. This corrects the earlier note "D4 steam ≈ 20 vs 1–3" — it is not a size effect.
  - `steam_heater_temp` D4 (`TIC420`) ranges 75–223 °C with only 1608 unique values (D1–D3 ≈ 7–8k) → different signal type; do not compare with D1–D3.
  - `LP_pressure` now has data in the cache and in `batch_master.csv` (1529 / 1540 batches), so the open issue "all NaN" is resolved.
- *Found by:* AI assistant (Claude), per-digester XGBoost-style feasibility check requested by the user.

**Next:** do not optimize Kappa from batch setpoints yet. Options: (1) model Kappa with slow features (daily/weekly drift, wood/chip, liquor strength) or a residual-after-daily-mean target; (2) pooled Viscosity model with alkali conc + cook time + P-factor; (3) fix/confirm steam flow tags (zero offset D1–D3, D4 range) with instrument team.

### 2026-10-27 — Viscosity-only surrogate (pooled vs partial pooling vs per digester)

**What was done:**

- Focus moved to Viscosity only (Kappa parked: dominated by slow drift). Local `batch_master.csv` only, no PI access; scratchpad scripts, no repo code changed.
- Data: `quality_flag == ok`, Viscosity 400–2000, all X present → **447 batches** (2026-07-01 → 2026-10-09; D1 108, D2 125, D3 129, D4 85).
- X and source tags: `alkali_accumulator1_conc` (`PM2.404AIC670:MV`, **shared**, mean HOT LIQUOR FILLING), `alkali_accumulator2_conc` (`PM2.404AIC667:MV`, shared), `pfactor_actual` (`PM2.10xDkPFACTOR.CALC`, last PREHYDROLYSIS), `heat_and_cook_minutes` (main sequence), `LP_pressure` (`PICk02:MV`, mean HEAT&COOK), `white_liquor_per_ton_chip` and `liquor_to_wood_ratio` (from `FIC532` + chip weight `WIk29`), Digester_ID dummies. Steam flow tags excluded (unreliable).
- Models: Ridge pooled, Ridge pooled + Digester_ID, Ridge partial pooling (per-digester slope as ridge-shrunk feature × digester terms), GBM depth 2 pooled (± Digester_ID), Ridge per digester. `TimeSeriesSplit(4)`; gate R² ≥ 0.30. Drop-one feature check, GBM permutation importance on the last 30%, quintile means, within-month / within-week correlation.

**Results:**

- **Gate not passed.** Out-of-time R² / MAE: baseline MAE 32.2; Ridge pooled 0.07 / 32.8; + Digester_ID 0.07 / 32.9; partial pooling 0.04 / 33.8; **GBM pooled 0.11 / 31.9** (best); Ridge per digester D1 0.01, D2 0.09, D3 −0.44, D4 0.25. Partial pooling is not better than pooled → no evidence the digesters respond differently; pooled is the right shape for now.
- **Main driver: `alkali_accumulator1_conc` (AIC670).** Removing it drops R² by 0.17 (others ≤ 0.03). Ridge ≈ −16 Viscosity per 1 g/l. Quintiles: ≤ 36.0 g/l → ~805; > 37.3 g/l → ~752 (monotonic).
- Secondary: P-factor actual > 361 → ~754 (other quintiles 790–800); heat&cook > 35 min → 761–770 vs 801 at ≤ 30 min. Alkali conc 2, LP_pressure and L:W add nothing. Signs match the chemistry (more alkali / longer cook → more cellulose degradation).
- **Caveat 1 — drift:** alkali vs Viscosity Spearman pooled −0.47, within-month −0.26, within-week −0.13; negative in every month (Jul −0.13, Aug −0.14, Sep −0.38, Oct −0.28). Monthly means move opposite (Oct alkali 37.9 / Viscosity 749). Part of the effect is slow co-movement — could be real (liquor strength changes slowly) or a shared confounder.
- **Caveat 2 — shared tag (corrects the earlier entry today):** AIC670 is one plant-level tag used for all digesters, so "same sign in all 4 digesters" for alkali is not independent evidence of a common digester response. The pooled choice still stands on the R² comparison.
- Status: alkali conc 1 is a strong **hypothesis** for Viscosity, not an operating window (model explains ~10%).
- *Found by:* AI assistant (Claude), Viscosity surrogate check requested by the user.

**Next:** (1) confirm with process team whether AIC670 is adjustable or a causticizing disturbance, and EA vs AA; (2) user to re-pull digester data back to Jan 2026 (≈3× data, helps separate drift); (3) add alkali charge per ton chip = conc × WL m³ / chip weight.

### 2026-10-27 — `XGboost_Model/` created; prehydrolysis speed and P-temp vs Viscosity

**What was done:**

- **New folder `XGboost_Model/`** (Viscosity only): `config.py` is the single edit point (`FEATURES` = batch_master column → plot label, one line each, with the PI tag in a comment), `data.py` (load/filter/coverage, `list_columns()`, `add_derived()`), `models.py` (baseline / Ridge / RF / sklearn GBM / XGBoost, `TimeSeriesSplit(4)` leaderboard, per-digester check), `explain.py` (feature-effect table: Spearman, Ridge per unit, RF/XGB permutation, XGB SHAP, drop-one, rank; binned means), `plots.py`, `01_compare.ipynb`, `README.md` (how to add a tag: A existing column / B new PI tag / C derived), `update.md`. `output/` is git-ignored. Installed `xgboost` 3.4.1 + `shap` 0.54.1 into system Python 3.13 (`C:\Python313\python.exe` = the notebook kernel; Python 3.12 lacks pandas).
- **Digester_Analysis:** `config.BATCH_FEATURES` += PREHYDRAU `pfactor_temp` (max, mean), `pfactor_temp_setpoint` (last), `mp_steam_valve` and `lp_steam_valve` (mean); `build_master.py` derives `pfactor_rate` = P-factor / prehydrolysis minutes. Rebuilt `batch_master.csv` and the phase tables from the local cache with `load_lab_samples(refresh=False)` — no PI pull. 76 → 82 columns; every old column identical.
- Analysis of the user question "low steam = slow prehydrolysis vs high steam = fast — does it matter?", and of the P-factor temperature (setpoint `OPESPPT`, actual `PFTEMP`).

**Results:**

- **Steam → time: yes.** MP steam valve % vs prehydrolysis minutes Spearman −0.62 / −0.63 / −0.42 / −0.57 (D1–D4); P-temp max −0.41 … −0.53. `steam_to_heater_flow` cannot confirm it (still no signal after removing the WAIT offset).
- **Time alone does not move Viscosity** (quintiles 784–793). **Speed does:** P-factor rate top quintile (> 4.66 /min) → ~762 vs 785–800; within-week Spearman −0.20 (P-factor amount drops to −0.01 within-week, so the earlier P-factor effect was mostly the season).
- **P-temp setpoint** exists for D2–D4 only (no D1 tag), almost always 162 / 163 / 164 °C. Actual P-temp max overshoots the setpoint by +3 to +4 °C; D1 (no setpoint tag) runs hottest (median 171.5 °C vs ~166–167). Setpoint drives speed (SP vs rate +0.31 … +0.54) but not minutes (≈ 0).
- Viscosity by P-temp SP (D2–D4): 162 °C → 809 (n 106), 163 → 780 (n 188), 164 → 772 (n 42). Confounded with time (162 °C only used Jul–Aug), but within Jul and Aug the order holds (Jul 796 / 789 / 750, Aug 819 / 805 / 767; n at 164 °C only 5–7). Sep is mixed (163 → 780, 164 → 788).
- Same P-factor setpoint, hot vs cool prehydrolysis (split at median P-temp max inside digester × PF-SP tertile): hot − cool = −6.0 Viscosity (p = 0.051); high PF-SP tertile −11.6 (p = 0.036). **Kappa unchanged (−0.03)** — hotter prehydrolysis gives no Kappa benefit but costs Viscosity (hypothesis: cellulose hydrolysis is more temperature-sensitive than the hemicellulose kinetics the P-factor is built on).
- Season confound: Jul → Oct the PF setpoint rose 340 → 430, P-temp SP 162 → 163, P-temp max 166.6 → 169.6 and alkali rose while Viscosity fell — several knobs moved together.
- **Model:** with `pfactor_rate`, P-temp max and MP valve, Ridge pooled R² 0.074 → **0.213** (MAE 29.4, best so far); XGBoost 0.121. Gate 0.30 still not passed. Linear > trees.
- *Found by:* AI assistant (Claude), from the user's flow / P-factor question.

**Next:** confirm with the process team why P-temp SP moved 162 → 163 °C (Sep) and the PF setpoint 340 → 430; propose a short trial: same PF setpoint, P-temp SP 162 vs 164 °C, watch Viscosity and Kappa. D1 P-temp setpoint tag to find.

### 2026-10-27 — Prehydrolysis detail: P-factor keeps rising after the phase

**What was done:**

- New `Digester_Analysis/prehydrolysis.py` (called from `build_master.py`; thresholds in `config.PH_TEMP_THRESHOLDS = [165, 168]`, steam phases in `config.STEAM_PHASES`) adds per batch: `pfactor_final` (max P-factor over PREHYDRAU + HOT LIQUOR FILLING), `pfactor_overshoot` (= final − setpoint), `ptemp_overshoot` (P-temp max − P-temp SP, D2–D4), `minutes_above_165` / `minutes_above_168` (PREHYDRAU), `steam_users_other` (mean number of other digesters in PREHYDRAU/HEAT&COOK during this PREHYDRAU). Master rebuilt from the local cache (`refresh=False`, no PI): 82 → 88 columns, all old columns identical.

**Results:**

- **P-factor does reach the setpoint** — the phase ends there (confirmed by the user). The negative `pfactor_gap` (median −15 … −23) is only the 5-min sampling: the last sample in PREHYDRAU comes just before the switch.
- **But the P-factor counter keeps rising during HOT LIQUOR FILLING** (digester still hot and acid until the white liquor neutralises it): final = setpoint **+67** median (P10 +43, P90 +100), e.g. SP 350 → 408. The overshoot follows the P-temp max (ρ +0.70). So the P-factor the chips really get is ~15–20% above the setpoint, and more when prehydrolysis runs hot.
- Viscosity, within-week Spearman (season removed): `pfactor_final` **−0.26** (strongest single X so far; alkali −0.13), overshoot −0.23, minutes > 165 °C −0.17, minutes > 168 °C −0.15, P-temp overshoot −0.11. **Kappa ≈ 0 for all of them** — the extra P-factor / heat buys no Kappa, only lower Viscosity.
- Bins: P-factor final > 469 → Viscosity 755 vs ~800 below 436; > 20 min above 168 °C → 755 vs 793 at 0 min.
- **Steam sharing (A4):** other digesters on steam make PREHYDRAU longer (ρ +0.44 with minutes) but do not change the P-factor rate (−0.03) and have no Viscosity effect within week (+0.03). Not the cause of the speed differences.
- **Model:** these features do not raise out-of-time R² (Ridge 0.17–0.18 vs 0.213) — they carry the same information as P-factor rate / P-temp max. Kept commented in `XGboost_Model/config.py` for easy switching.
- *Found by:* AI assistant (Claude), user question on P-factor ending at setpoint + A1/A2/A4.

**Next:** ask the process team whether the P-factor after PREHYDRAU (HLF overshoot) is known/controlled; candidates to test in a trial: lower P-temp SP (162 °C), or PF setpoint that targets the *final* P-factor.

### 2026-10-28 — Golden Batch section added to `02_analysis.ipynb`

**What was done:**

- Added a **"Golden Batch analysis (Golden vs Non-Golden)"** section at the end of `Digester_Analysis/02_analysis.ipynb` (1 markdown + 4 code cells). Golden is **defined from Y** via the existing `overall_grade` column (no new numeric cut): Golden = `overall_grade == "normal"` (both Kappa 8–10 **and** Viscosity 700–800 in band), Non-Golden = `abnormal`, batches with no lab dropped. Scope = pooled over D1–D4 (`digester` kept only as a split-check). X = union of the notebook's Step 1–4 lists (22 params). Reuses existing `MIN_N`, `LAB_LABELS`, `master` (already `quality_flag=="ok"`). No PI access; local CSV only. Validated headless against real data via `.venv` (all four cells run clean; temp scripts removed).
- Four views: (1) split counts overall + per digester; (2) **Mean + Variance (SD)** per X, Golden vs Non-Golden, with mean diff + Mann–Whitney U *p* + Cliff's delta, sorted by |delta|; (3) **Spearman** of each X vs Kappa/Viscosity (pooled) + heatmap; (4) **distribution** KDE Golden vs Non-Golden per X + Golden p10–p90 window table.

**Results (654 graded batches: 251 Golden / 403 Non-Golden):**

- Golden share by digester: D1 51.9%, D3 42.1%, D2 29.6%, D4 26.4% — Golden spans all digesters, not one.
- Largest Golden-vs-Non-Golden separation (|Cliff's d|, MWU p<0.05): black_liquor_conductivity_mean_displacement −0.33, prehydrolysis_minutes −0.28, h_factor +0.27, ventilation_temp_max_chip_filling −0.25, digester_pressure_max_prehydrolysis +0.20, liquor_to_wood_ratio +0.19 — all small-to-medium effects only.
- Consistent with earlier logs: effects are weak and are **hypotheses** (no lag/production adjustment; grade bands 8–10 / 700–800 still unconfirmed with the process team). Note `summaryUpdate.md`'s earlier "Kappa 9.0–9.5 / Viscosity 725–775" line is stale — `config.QUALITY_TARGETS` is **Kappa (8,10) / Viscosity (700,800)**.
- *Found by:* AI assistant (Copilot), Golden Batch request from the user.

**Next:** confirm the grade bands with the process team; if wanted, add Cliff's-delta CIs / KS test, or compute an alkali-charge-per-ton-chip X and re-run the Golden split.

### 2026-10-28 — Golden Batch split **by digester** added to `02_analysis.ipynb`

**What was done:**

- Extended the Golden Batch section with a **"Golden vs Non-Golden, split by digester"** subsection (1 markdown + 4 code cells, ids `golden-dig-*`). Same Golden definition (`overall_grade`), same 22 X, but every view is computed per digester D1–D4. Reuses the pooled cells' `graded/golden/nongolden/GOLDEN_X/cliffs_delta/golden_window/MIN_N/LAB_LABELS`. No PI access; local CSV only. Validated headless against real data via `.venv` (all four cells run clean; temp scripts removed).
- Four per-digester views: (5) **Mean + Variance (SD)** per X per digester (`golden_compare_dig`), Golden vs Non-Golden with mean diff + MWU p + Cliff's delta; (6) **Cliff's-delta heatmap** rows=X, cols=D1–D4 (look for a sign that holds across digesters = repeatable hypothesis); (7) **Spearman** rho of each X vs Kappa/Viscosity, one heatmap per Y with a column per digester; (8) **distribution** KDE of each X within Golden, one line per digester, plus a per-digester Golden p10–p90 window table.
- Later added **view (9)** `golden_vs_non_by_digester(x)` (id `golden-dig-code-09`): for one chosen X, a panel per digester with **Golden vs Non-Golden overlaid** (green vs red) — answers "within each digester, do the good vs bad batches separate on this X?". Pick the X by editing the column name; defaults to `black_liquor_conductivity_mean_displacement`. Validated headless. **Switched from KDE to ECDF (cumulative)** at the user's request: at small per-digester n (esp. D4=28) ECDF has no bandwidth artifact, reads percentiles directly off the Y axis, and the line further LEFT = lower values with the largest vertical gap = best group separation.

**Results / caveat:**

- Per-digester graded n: **D1 83G/77N, D2 55G/131N, D3 85G/117N, D4 28G/78N.** D4 Golden (n=28) is small — treat its per-digester numbers as noisy.
- Purpose is to check whether a pooled "Golden driver" is consistent across digesters or an artifact of one; the heatmaps make sign-consistency easy to scan. Effects remain **hypotheses** (small per-digester n, no lag/production adjustment, grade bands still unconfirmed).
- *Found by:* AI assistant (Copilot), follow-up "แยกตาม digester" request from the user.

**Tooling note:** `editNotebook` / `runNotebookCell` were unavailable in this environment; cells were appended by editing the `.ipynb` JSON directly (Python script) and validated headless with `matplotlib` Agg against `build_master.load_outputs()`. This workaround is the reliable path for future notebook edits here.
