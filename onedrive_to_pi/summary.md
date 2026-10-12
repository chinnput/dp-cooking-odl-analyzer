# Summary of `onedrive_to_pi` Workspace

## Project Overview

The **OneDrive to PI Sync Pipeline** extracts pulp mill quality lab measurements (Kappa, Viscosity, Brightness) from daily/monthly Excel Log Books, cleans and formats the data, and pushes it to the **AVEVA PI Server** (`VPKGDRBPPI01`) via Historical API (`write_old`) or Real-Time API for visualization on **PI Vision** dashboards.

---

##  Scripts & Core Responsibilities

| Script Name                             | Purpose & Functionality                                                                                                                                                                     |       Status       |
| :-------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :-----------------: |
| **`config.py`**                 | Central configuration: Dynamic OneDrive folder resolution, column coordinates for 19 PI Tags, Local Gateway (`write_old`) & MI Cube API settings, and PI Tag Mappings.                  | 🟢 Production Ready |
| **`step0_download_sharepoint.py`**| Auto-downloads the latest Excel Log Book from SCG SharePoint Online using Playwright. Robust save with unique temp names + retry (`_safe_save_download`) to survive locked files, interactive login wait up to 5 min (`_wait_for_login`), and UTF-8 stdout to avoid emoji encoding crashes. | 🟢 Production Ready |
| **`step1_fetch_onedrive.py`**   | Scans monthly Excel Log Books, infers dates from sheet names (`1`–`31`), selects the correct file per **(year, month)** inferred from the filename (handles `9.` vs `09.`, ignores `_quarantine_`), extracts 19 lab parameters, and builds exact timestamps. | 🟢 Production Ready |
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

---

## Troubleshooting History & Safeguards (ประวัติการแก้ปัญหาและการป้องกัน)

> อัปเดตล่าสุด: 2026-10-02

### อาการที่เคยเจอ: "เข้าเดือนใหม่แล้วข้อมูลไม่อัพเดต" / "ข้อมูลไม่มาหลังวันที่ 24/09 แม้ SharePoint มีข้อมูล"

**Root causes ที่พบ (หลายชั้น):**

1. **เลือกไฟล์ Excel ผิด** — `step1` เดิมเลือกไฟล์ตาม modification time (mtime) ล่าสุด ทำให้ไฟล์เดือนเก่า (เช่น Sep) ที่เพิ่งถูก OneDrive sync มา mtime ใหม่กว่า ไปชนะไฟล์เดือนปัจจุบัน (Oct) → อ่านข้อมูลผิดเดือน
2. **ชื่อไฟล์ไม่สม่ำเสมอ** — มีทั้ง `9.` และ `09.` ทำให้ dedup แบบเทียบชื่อ string มองเป็นคนละไฟล์ เกิดไฟล์เดือนเดียวกันซ้อนกันหลายตัว
3. **`Permission denied` ตอนดาวน์โหลด** — ไฟล์ `.xlsx`/`.tmp` ถูกล็อกโดย Excel/OneDrive ทำให้ `download.save_as(.tmp)` ล้มเหลว → การดาวน์โหลดเดือนใหม่ไม่สำเร็จ แล้ว fallback ใช้ไฟล์เก่า
4. **Encoding crash** — การ `print()` อักขระ unicode/emoji (`\u2705`) บน Windows console (cp874) ทำให้ download logic หยุดกลางคัน
5. **Login SharePoint เร็วเกินไป** — รอ login แค่ 25 วินาที และรันแบบ headless ทำให้มองไม่เห็นหน้า login/กรอก MFA ไม่ทัน
6. **บั๊กการเดาปีจากชื่อไฟล์** — ไฟล์ `...2025 in JAN 2026.xlsx` ถูกเดาปีเป็น 2025 (regex จับ `2025` ตัวแรก)

### การแก้ไขที่ลงไปแล้ว (Fixes applied)

**`step0_download_sharepoint.py`**
- เพิ่ม `_safe_save_download()` — ดาวน์โหลดไปที่ temp ชื่อไม่ซ้ำ (`<file>.<pid>.<epoch>.tmp`) แล้ว retry `os.replace()` สูงสุด 5 รอบ เพื่อกัน `Permission denied` เมื่อไฟล์ถูกล็อก; ถ้าล็อกจริงจะเก็บสำเนาใหม่เป็น `.tmp` (ไม่สูญข้อมูล)
- เพิ่ม `_is_login_page()` + `_wait_for_login()` — poll ทุก 3 วินาที รอ login สำเร็จจริงสูงสุด 5 นาที (`login_wait_seconds=300`) แทนการ sleep คงที่
- ตั้ง `sys.stdout/stderr` เป็น UTF-8 (`errors="replace"`) — กัน encoding crash จาก emoji/unicode

**`step1_fetch_onedrive.py`**
- เปลี่ยนการเลือกไฟล์จาก "mtime ล่าสุด" → **dedup ตาม (ปี, เดือน) ที่อนุมานจากชื่อไฟล์** (`9.` กับ `09.` = เดือนเดียวกัน) และภายในเดือนเดียวกันเลือก mtime ใหม่สุด
- เรียงไฟล์ตาม (ปี, เดือน) → เดือนล่าสุดอยู่ท้ายเสมอ (hourly mode เลือกเดือนปัจจุบันถูกต้อง)
- ข้ามโฟลเดอร์ `_quarantine_*` ไม่ให้ไฟล์เก่าถูกหยิบมาใช้
- แก้ `infer_year_month_from_fname()` — ดึงปีจากเลขปีที่อยู่**หลังชื่อเดือน** (เช่น "JAN 2026") ก่อน แล้ว fallback เป็นปีสุดท้ายในชื่อ → แก้บั๊กปี 2025

**`main_sync.py`**
- Step 0 เปลี่ยนจาก `headless=True` → `headless=False` + `login_wait_seconds=300` เพื่อให้เห็นหน้า login และ reuse session ผ่าน persistent profile ในครั้งถัดไป

### การจัดการไฟล์ในเครื่อง (ไม่กระทบ SharePoint)
- ไฟล์ซ้ำ/ค้าง (`.tmp` เก่า, Sep/Oct เวอร์ชันเก่า) ถูกย้ายไปโฟลเดอร์ `_quarantine_<timestamp>` (กู้คืนได้) ไม่ได้ลบถาวร
- ไฟล์ Oct ใหม่สุด (`.tmp`) ถูก promote เป็น `.xlsx` canonical
- หมายเหตุ: Step 0 เป็นการ **download ทางเดียว** เท่านั้น ไม่มีการ upload/delete กลับไปที่ SharePoint

### ความเสี่ยงที่ยังเหลือ (Known risks / แนะนำทำต่อ)
1. **ไฟล์ถูกล็อก** — ถ้าไฟล์เดือนใหม่ถูกเปิดค้างใน Excel/OneDrive อาจมี `.tmp` ค้างสะสม (ยังอ่านได้ แต่ควรมีการล้างอัตโนมัติ) — *แนะนำ: ล้าง `.tmp` ค้างตอนเริ่ม Step 0*
2. **`last_sync_timestamp` เป็นค่าเดี่ยว (ไม่ใช่ per-tag)** — ถ้ามี tag ถูกกรอกย้อนหลังในชีท อาจไม่ถูกจับ — *แนะนำ: เปลี่ยนเป็น `last_sync_by_tag`*
3. **ชื่อไฟล์ SharePoint เปลี่ยนรูปแบบ** — ระบบพึ่งพาการเดาเดือนจากชื่อไฟล์ ถ้ารูปแบบเปลี่ยนมาก การเลือกไฟล์อาจผิด
4. **ไม่มี alert เมื่อ sync ค้าง** — *แนะนำ: เพิ่ม health-check เตือนเมื่อ `last_sync_timestamp` ไม่ขยับเกิน N ชั่วโมง*

### วิธีทดสอบ (dry-run, ปลอดภัย ไม่ส่งจริง)
```powershell
cd "d:\chinnput\DP Cooking ODL Analyzer\onedrive_to_pi"
python dry_run_payloads.py
```
ตรวจผล: `Found N Excel file(s)` ต้องมีไฟล์เดือนปัจจุบัน, `Latest Timestamp in Excel` ต้องขยับถึงเดือนปัจจุบัน, และ `Total payloads prepared > 0` เมื่อมีข้อมูลใหม่
