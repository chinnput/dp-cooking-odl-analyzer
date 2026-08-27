# Summary of `onedrive_to_pi` Workspace

## 📌 Project Overview
The **OneDrive to PI Sync Pipeline** extracts pulp mill quality lab measurements (Kappa, Viscosity, Brightness) from daily/monthly Excel Log Books, cleans and formats the data, and pushes it to the **AVEVA PI Server** (`VPKGDRBPPI01`) via Historical API (`write_old`) or Real-Time API for visualization on **PI Vision** dashboards.

---

## 🛠️ Scripts & Core Responsibilities

| Script Name | Purpose & Functionality | Status |
| :--- | :--- | :---: |
| **`config.py`** | Central configuration: Dynamic OneDrive folder resolution, column coordinates, Historical API (`write_old`) & MI Cube API settings, and 13 PI Tag Mappings. | 🟢 Production Ready |
| **`step1_fetch_onedrive.py`** | Scans monthly Excel Log Books, parses all daily sheets (`1`–`31`), extracts lab parameters, and builds exact timestamps. | 🟢 Production Ready |
| **`step2_time_matching.py`** | Sorts lab measurements strictly chronologically and handles historical backfill or incremental filtering against `sync_state.json`. | 🟢 Production Ready |
| **`step3_pi_api_client.py`** | Converts DataFrame records into historical JSON payloads (`tag`, `value`, `timestamp`) and sends HTTP POST requests sequentially to `write_old` API with detailed terminal logging. | 🟢 Production Ready |
| **`main_sync.py`** | Main orchestrator: Executes **Step 1 ➔ Step 2 ➔ Step 3** sequentially (`dry_run` preview & live mode supported). | 🟢 Production Ready |
| **`sync_state.json`** | State tracker: Records processed files and latest sync timestamps to prevent duplicate data transmission. | 🟢 Production Ready |
| **`run_pi_sync.bat`** | Windows Batch runner for scheduling automated execution via **Windows Task Scheduler**. | 🟢 Production Ready |
| **`test_api_connection.py`** | Diagnostic utility to test MI Cube API authentication and payload connectivity. | 🟢 Diagnostic Tool |
| **`test_write_old_api.py`** | Diagnostic utility to test historical API endpoint (`write_old`). | 🟢 Diagnostic Tool |
| **`test_read_interpolated.py`**| Diagnostic utility to query and verify historical interpolated data from PI Server. | 🟢 Diagnostic Tool |

---

## 🏷️ Extracted Lab Parameters (13 PI Tags)
* **Kappa no. (3 Tags):** `PULP-LINE2-KAPPA-PRESS1`, `PULP-LINE2-KAPPA-PRESS3`, `PULP-LINE2-KAPPA-EOP`
* **Viscosity (6 Tags):** `PULP-LINE2-VISCOSITY-PRESS1`, `PULP-LINE2-VISCOSITY-PRESS3`, `PULP-LINE2-VISCOSITY-D0`, `PULP-LINE2-VISCOSITY-EOP`, `PULP-LINE2-VISCOSITY-D1`, `PULP-LINE2-VISCOSITY-D2`
* **Brightness (4 Tags):** `PULP-LINE2-BRIGHTNESS-PRESS1`, `PULP-LINE2-BRIGHTNESS-PRESS3`, `PULP-LINE2-BRIGHTNESS-D0`, `PULP-LINE2-BRIGHTNESS-EOP`

---

## 🔑 Key API Endpoints & Behavior
1. **Historical Write Endpoint (`write_old`)**: `http://10.28.58.72:8123/write_old`
   - Header: `Authorization: Bearer <TOKEN>`
   - Payload: `{"tag": "...", "value": "...", "timestamp": "YYYY-MM-DD HH:MM:SS"}`
   - Behavior: Writes historical values directly into PI Archive at exact timestamps.
2. **Real-Time Snapshot Endpoint (`WriteValue/ByTag/`)**: `https://micube.scg.com/v2/api/Datacenter/PIServer/WriteValue/ByTag/`
   - Payload: `{"token": "...", "server": "...", "tag": "...", "value": float}`
   - Behavior: Writes snapshot value at current server time.

