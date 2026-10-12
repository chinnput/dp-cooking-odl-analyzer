---
name: dp-cooking-odl
description: Project map and working rules for the DP Cooking ODL Analyzer repo (SCG Pulp Line 2, Digesters D1–D4, ODL / Press 1 quality). Use it for ANY task in this workspace, including the Press 1 notebook, digester assignment (Bk_Discharge_FinalTime_Press1_Status), the onedrive_to_pi lab-to-PI sync, the PI write_old gateway, PI AF lag-time logic, MI Cube API pulls, the Pteam batch-clustering scripts, and Kappa / Viscosity / Brightness analysis. It also applies when the user only says things like "หม้อต้มไหน", "Press 1", "sync ไม่อัพเดต", "lab tag", "lag time" or "update summary".
---

# DP Cooking ODL Analyzer

## What the project is

The project analyzes process variation in **DP Cooking (batch digesters D1–D4)** and **ODL (Oxygen Delignification) washing** on **Pulp Line 2** at SCG (site PPPC). The current phase is **"Just Visualize, Not Optimize"**: build reliable data pipelines and show variation clearly before proposing any process change.

- **Y (quality):** Press 1 lab Kappa, Viscosity and Brightness (`PULP-LINE2-*-PRESS1`).
- **X (process):** DCS tags from PI, such as White Liquor, MP Steam, Production ODL, Press 1 consistency and Deknotting flow.
- **Core question:** which digester's pulp is at Press 1 at time t, and does quality differ by digester?

## Read first, in this order

1. `DP Cooking ODL Analyzer/summaryUpdate.md` is the **living project log**: current state, open issues, and dated findings with "Found by". Treat it as the source of truth for the latest status. It changes often, so read it each time.
2. `DP Cooking ODL Analyzer/Pteam/Lag_Time_Sequence.md` (Thai) documents the 9-step PI AF logic that maps a digester discharge to Press 1, AF issues A–I, and the After-Press-3 plan. See [references/lag-chain.md](references/lag-chain.md) for the short version.
3. `onedrive_to_pi/summary.md` covers the sync pipeline, the troubleshooting history (Thai) and known risks.
4. `DP Cooking ODL Analyzer/tag_summary.md` (Thai) lists the 19 lab tags with their Excel columns and the 31 DCS parameters. See [references/tags.md](references/tags.md).
5. `onedrive_to_pi/agent_instructions.md` sets the user's working rules, summarized below.

## Repo layout

| Path | What it is | Status |
|---|---|---|
| `DP Cooking ODL Analyzer/Lab_Analysis/realtime_pi_press1_analysis.ipynb` | **Main current work.** Pulls 12 tags from the MI Cube API (interpolated), assigns Digester_ID, and builds KDE, histograms with summary tables, boxplots, SOP heatmaps, mean/median heatmaps and per-digester correlations. | Active |
| `DP Cooking ODL Analyzer/Lab_Analysis/data/*.csv.gz` | Cache of 1-minute PI pulls (status and lab). Git-ignored. | Cache |
| `DP Cooking ODL Analyzer/Pteam/` | Phase 1 work from the previous owner (May–Jul 2026): batch signatures, PCA clustering into Normal/Abnormal, SOP percentile limits, digester comparison, specific consumption. Uses the Excel inputs/outputs in the same folder. | Historical |
| `onedrive_to_pi/` | Production pipeline: SharePoint log book (Excel) → 19 lab PI tags. Steps 0→3 run from `main_sync.py`. | Production |
| `PI_gateway_for_write_old_data/app_pro/` | Local FastAPI gateway (`uvicorn app_pro.main:app --port 5707 --workers 2`) that uses OSIsoft AFSDK via pythonnet (`clr`) plus redis. Endpoints: `/fetch`, `/special_fetch/`, `/write`, `/write_old`. | Production |
| `skillsAI/process-gap-analysis/` | Editable copy of the general process-gap-analysis skill. | Tooling |
| `Doc/` | PP101 pulp-making training, the Line 2 ODL tag list, and DP formula slides (pptx/pdf). | Reference |

Pteam pipeline order (run from inside `Pteam/`): `clean_data.py` → `extract_signatures.py` → `cluster_analysis.py` → `generate_sop_reference.py` → `main_analysis.py` → `analyze_digester_performance.py` → `visualize_*` → `integrity_check.py`.

## Data flow

```
SharePoint log book (Excel, 1 file/month, sheets "1".."31")
  └─ onedrive_to_pi: step0 download (Playwright, visible SSO) → step1 parse → step2 filter (3-day lookback) → step3 POST
        └─ write_old gateway 127.0.0.1:5707 (AFSDK) ─→ PI Server VPKGDRBPPI01 ←─ DCS tags (PM2.*)
PI AF \\VPKGDCIPS01\iPMS, element PPPC_DP_Cooking ─→ writes Bk_Discharge_FinalTime_Press1_Status (value k or 0)
PI ─→ MI Cube API  https://micube.scg.com/v2/api/Datacenter/PIServer/InterpolatedValue/MultiTag/ ─→ notebook
```

## Key rules and logic you must respect

- **Digester assignment (notebook `get_active_digester`):** a row is Dk only if `Bk == k` exactly and no other digester matches. Otherwise it is NaN. This was a deliberate decision on 2026-10-06: drop about 17% of rows rather than mislabel them. Don't revert to `> 0` (it over-counted D1, 56% vs a true 26.5%), and don't add carry-forward heuristics without asking.
- **PI interpolates the status and lab tags linearly** (`Step = 0`), and AF Step 8 uses `InterpolatedValues`, so about 20% of recorded status points are fractional (0.5, 1.95, 3.2187). The proper fix is in AF and PI (`PrevVal` and/or `Step = 1`), not in Python.
- **Notebook N counts interpolated points, not real lab samples.** Kappa and Viscosity are sampled every 4 h, Brightness every 2 h. Say this whenever you report N or significance.
- **Spike filters:** Viscosity 400–2000, Brightness 25–50. Apply the same filter to the plot and its summary table.
- **SOP limits** (`LAB_SOP_LIMITS`: Kappa 7.5–8.5, Viscosity 680–710, Brightness 37–40) are **unconfirmed**. Almost all data falls outside them. Don't present "% in SOP" as a verdict.
- **Specific consumption** = `24 × flow / Production ODL (ADT/D)`, with production ≤ 0 set to NaN. It spikes like 1/x during slowdowns, which is the main "Abnormal" class.
- **Lag model** = steady state, residence time = V/Q. Don't flag that as a bug, but note it breaks during slowdown and trip batches.
- **Correlations** from hourly interpolated data with no adjustment for lag or production are **hypotheses**, not findings.

## Safety and gotchas

- **`python main_sync.py` with no arguments runs LIVE** (`dry_run=False`) and writes to PI. For a safe test use `python dry_run_payloads.py` or `run_pipeline(dry_run=True)`. Never run a live sync, the `--loop` mode or `test_write_old_api.py` without explicit approval.
- `sync_state.json` (`last_sync_timestamp` plus the 3-day pushed history) controls what is resent. Don't edit or delete it casually.
- **Secrets:** the MI Cube token lives in `.env` as `MI_CUBE_API_TOKEN` and is git-ignored. Hard-coded tokens still exist in `onedrive_to_pi/config.py`, the `test_*.py` scripts and the gateway `GATEWAY_TOKEN` default. Never print, copy or commit token values, and redact them in any output.
- `onedrive_to_pi/summary.md` mentions `10.28.58.72:8123/write_old`, but `config.py` uses the local gateway `127.0.0.1:5707`. Trust `config.py`.
- The gateway needs Windows, the AFSDK assembly and redis. It can't run elsewhere.
- Windows console encoding is cp1252/cp874, and Thai text, σ or emoji will crash `print`. Set `PYTHONIOENCODING=utf-8` and use `.venv/Scripts/python.exe` (Python 3.11: pandas 3, seaborn, sklearn, scipy, playwright, python-dotenv).
- `onedrive_to_pi/OneDrive_*` holds many `.xlsx.*.tmp` files from locked downloads. They are expected and git-ignored. Old copies go to `_quarantine_*` folders, which are never deleted.
- The move of the old root scripts into `Pteam/` shows in git as deletions plus untracked files until it is committed. That is expected, so don't "restore" the deleted files.
- The notebook fallback reads `df_clustered_batches.xlsx` by relative path, so it only works when cwd is `Pteam/`.
- All PI timestamps are plant local time (Asia/Bangkok, no tz suffix).

## How the user wants you to work

- **Ask before ANY action.** Before editing files, running scripts, pulling data or running an analysis, describe the plan and wait for explicit approval ("approve", "do it", "แก้เลย"). Approval for one step doesn't cover the next.
- **Never access PI**, not even read-only. That covers the MI Cube API, PI AF / AF SDK, PI Server `VPKGDRBPPI01` and the write_old gateway. Use local data only (`Lab_Analysis/data/`, the log books, files the user provides). If PI data is needed, ask the user to pull it.
- **Nothing risky:** no live syncs, no writes to PI, no deleting or overwriting without approval.
- Keep the code **simple and readable** with no over-engineering, matching the notebook's existing style of plain helpers and module-level config constants.
- Keep replies **short and substantive**. The user often writes in Thai, so reply in their language and keep technical terms in English.
- Offer a **dry-run** for anything that touches PI, SharePoint or state files.
- Print clear item-by-item progress in scripts.
- After meaningful analysis or a change, **update `summaryUpdate.md`**: Current State, plus a dated Progress Log entry with **What was done / Results / Found by**. Use absolute dates and note commit hashes.

## Domain glossary (short)

- **Kappa:** residual lignin. Lower means more delignified.
- **Viscosity** (cm³/g): fiber strength / degree of polymerization.
- **Brightness** (%): how white the pulp is.
- **ADT/D:** air-dry tons per day.
- **White Liquor:** NaOH + Na₂S cooking chemical.
- **ODL:** O₂ delignification reactors 1 and 2.
- **Press 1/2/3:** wash presses. Press 1 comes after screening and before ODL.
- **LC chest:** low-consistency storage chest.
- **Discharge tank:** 800 m³ tank shared by D1–D4, FIFO.
- **DP** = displacement batch cooking. Each digester runs the sequence CHIP FILLING → HOT LIQUOR → … → DISCHARGE → WAIT.
