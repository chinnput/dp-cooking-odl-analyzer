# Summary of `onedrive_to_pi` Workspace

## Project Overview

The **OneDrive to PI Sync Pipeline** extracts pulp mill quality lab measurements (Kappa, Viscosity, Brightness) from daily/monthly Excel Log Books, cleans and formats the data, and pushes it to the **AVEVA PI Server** (`VPKGDRBPPI01`) via Historical API (`write_old`) or Real-Time API for visualization on **PI Vision** dashboards.

---

##  Scripts & Core Responsibilities

| Script Name                             | Purpose & Functionality                                                                                                                                                                     |       Status       |
| :-------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :-----------------: |
| **`config.py`**                 | Central configuration: Dynamic OneDrive folder resolution, column coordinates for 19 PI Tags, Local Gateway (`write_old`) & MI Cube API settings, and PI Tag Mappings.                  | 🟢 Production Ready |
| **`step0_download_sharepoint.py`**| Auto-downloads the latest Excel Log Book directly from SCG SharePoint Online using Playwright with atomic file replacement to prevent Windows permission locks.                     | 🟢 Production Ready |
| **`step1_fetch_onedrive.py`**   | Scans monthly Excel Log Books, infers dates from sheet names (`1`–`31`) to handle copy-paste header errors, prioritizes fresh downloaded `.tmp` files, extracts 19 lab parameters, and builds exact timestamps. | 🟢 Production Ready |
| **`step2_time_matching.py`**    | Sorts lab measurements strictly chronologically. Features a **3-Day Lookback Window** with record-level deduplication to automatically catch backfilled lab entries.                   | 🟢 Production Ready |
| **`step3_pi_api_client.py`**    | Converts DataFrame records into historical JSON payloads (`tag`, `value`, `timestamp`) and sends HTTP POST requests sequentially to `write_old` API with detailed terminal logging. | 🟢 Production Ready |
| **`main_sync.py`**              | Main orchestrator: Executes **Step 0 ➔ Step 1 ➔ Step 2 ➔ Step 3** sequentially (`dry_run` preview, `hourly`, `new_tags_only`, and `backfill` modes supported).                             | 🟢 Production Ready |
| **`sync_state.json`**           | State tracker: Records processed files and latest sync timestamps to prevent duplicate data transmission.                                                                                   | 🟢 Production Ready |
| **`run_pi_sync.bat`**           | Windows Batch runner for scheduling automated execution via**Windows Task Scheduler**.                                                                                                | 🟢 Production Ready |
| **`test_api_connection.py`**    | Diagnostic utility to test MI Cube API authentication and payload connectivity.                                                                                                             | 🟢 Diagnostic Tool |
| **`test_write_old_api.py`**     | Diagnostic utility to test historical API endpoint (`write_old`).                                                                                                                         | 🟢 Diagnostic Tool |
| **`test_read_interpolated.py`** | Diagnostic utility to query and verify historical interpolated data from PI Server.                                                                                                         | 🟢 Diagnostic Tool |

---

## Extracted Lab Parameters (19 PI Tags)

* **Kappa no. (3 Tags):** `PULP-LINE2-KAPPA-PRESS1`, `PULP-LINE2-KAPPA-PRESS3`, `PULP-LINE2-KAPPA-EOP`
* **Viscosity (6 Tags):** `PULP-LINE2-VISCOSITY-PRESS1`, `PULP-LINE2-VISCOSITY-PRESS3`, `PULP-LINE2-VISCOSITY-D0`, `PULP-LINE2-VISCOSITY-EOP`, `PULP-LINE2-VISCOSITY-D1`, `PULP-LINE2-VISCOSITY-D2`
* **Brightness (6 Tags):** `PULP-LINE2-BRIGHTNESS-PRESS1`, `PULP-LINE2-BRIGHTNESS-PRESS3`, `PULP-LINE2-BRIGHTNESS-D0`, `PULP-LINE2-BRIGHTNESS-EOP`, `PULP-LINE2-BRIGHTNESS-D1`, `PULP-LINE2-BRIGHTNESS-D2`
* **pH (4 Tags):** `PULP-LINE2-PH-D0`, `PULP-LINE2-PH-EOP`, `PULP-LINE2-PH-D1`, `PULP-LINE2-PH-D2`

---

## Key API Endpoints & Behavior

1. **Historical Write Endpoint (`write_old`)**: `http://10.28.58.72:8123/write_old`
   - Header: `Authorization: Bearer <TOKEN>`
   - Payload: `{"tag": "...", "value": "...", "timestamp": "YYYY-MM-DD HH:MM:SS"}`
   - Behavior: Writes historical values directly into PI Archive at exact timestamps.
2. **Real-Time Snapshot Endpoint (`WriteValue/ByTag/`)**: `https://micube.scg.com/v2/api/Datacenter/PIServer/WriteValue/ByTag/`
   - Payload: `{"token": "...", "server": "...", "tag": "...", "value": float}`
   - Behavior: Writes snapshot value at current server time.
