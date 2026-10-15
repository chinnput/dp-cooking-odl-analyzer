# Digester_Analysis: วิเคราะห์ Batch Digester (D1–D4) ของ Pulp Line 2

วิเคราะห์การต้มของหม้อ D1–D4 ทีละ batch แล้วผูกเข้ากับคุณภาพที่ Press 1 (Kappa, Viscosity, Brightness) เพื่อตอบคำถาม 2 ข้อ:

1. หม้อแต่ละใบ cook แต่ละ batch **ต่างกันแค่ไหน** (ความนิ่งของ process)
2. **ค่าการ cook ตัวไหน** สัมพันธ์กับคุณภาพที่ Press 1

> ปรับปรุงล่าสุด: 2026-10-15 · ข้อมูลที่ใช้ตอนนี้: 2026-08-01 → 2026-10-01 (5 นาที)

---

## 1. ภาพรวม: ข้อมูลไหลยังไง

```
 PI (MI Cube)                      Log book Excel (SharePoint → onedrive_to_pi)
     │ python pull_data.py              │ อ่านเฉพาะ sample จริง (ไม่ใช้ค่าที่ PI interpolate)
     ▼                                  ▼
 data/digester_<start>_<end>.csv   data/lab_samples.csv
 (sensor ทุก 5 นาที, 99 tag)        (Kappa/Visc/Bright ตามเวลาที่ lab วัดจริง)
     │                                  │
     └──────────► 01_build_master.ipynb ◄──────────┘
                        │  (build_master.py)
                        ▼
      data/batch_master.csv   (1 แถว = 1 batch)
      data/lab_linked.csv     (1 แถว = 1 lab sample พร้อม digester และ batch)
                        │
                        ▼
                02_analysis.ipynb  (อ่าน CSV อย่างเดียว เร็ว แก้เล่นได้)
```

**หลักสำคัญ:** ทุกอย่างถูกแปลงให้อยู่ระดับ **batch** ก่อนวิเคราะห์ เพราะการ cook เกิดเป็น batch

- Sensor 5 นาที → สรุปเป็นค่าต่อ batch ตาม phase (เช่น max temp ช่วง HEAT&COOK)
- Lab รายชั่วโมง → ผูกเข้า batch ที่เยื่อนั้นมาจาก

---

## 2. วิธีใช้ (ทำตามลำดับ)

| เมื่อไหร่                         | ทำอะไร                                                                                                                                       | หมายเหตุ                                                                                             |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| ต้องการข้อมูลช่วงใหม่ | 1) แก้ `START_TIME` / `END_TIME` ใน `config.py`  2) `cd "DP Cooking ODL Analyzer/Digester_Analysis"` แล้ว `python pull_data.py` | ขั้นนี้ขั้นเดียวที่ต่อ PI ต้องมี `MI_CUBE_API_TOKEN` ใน `.env` ที่ root |
| หลัง pull ข้อมูลใหม่         | เปิด `01_build_master.ipynb` → **Run All**                                                                                            | สร้างและ save ตาราง ดู section 3–6 (การตรวจสอบ) ทุกครั้ง                   |
| วิเคราะห์                         | เปิด `02_analysis.ipynb` → **Run All**                                                                                                | อ่านแค่ CSV ไม่กี่วินาที                                                                  |
| มี lab ใหม่ใน log book             | ใน `01_build_master.ipynb` เปลี่ยนเป็น `load_lab_samples(refresh=True)` แล้วรันใหม่                                    | อ่าน Excel ใหม่ทั้งหมด                                                                        |

ทั้งสอง notebook มี `%autoreload 2` อยู่แล้ว **แก้ไฟล์ `.py` แล้วรัน cell ใหม่ได้เลย ไม่ต้อง restart kernel**

---

## 3. ไฟล์ในโฟลเดอร์

| ไฟล์                               | หน้าที่                                                                                                                                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `config.py`                          | **ตั้งค่าทุกอย่างที่นี่:** ช่วงเวลา, tag แยกหมวด, ชื่อ phase, phase ที่ใช้คิด H-factor, รายการ batch feature, SOP, เกณฑ์ quality flag |
| `pull_data.py`                       | ดึง tag จาก PI ทีละสัปดาห์ แล้ว save เป็น CSV (`python pull_data.py`)                                                                                                        |
| `batch.py`                           | แบ่ง phase และ batch จาก `main_sequence`, คำนวณ batch features, quality flag                                                                                                           |
| `hfactor.py`                         | H-factor (หลักการอยู่ในข้อ 5)                                                                                                                                                           |
| `lab.py`                             | อ่าน lab จริงจาก log book, ระบุ digester, ผูกเข้า batch                                                                                                                           |
| `build_master.py`                    | รวมทุกขั้นเป็น `build_master()` ฟังก์ชันเดียว, save/load CSV                                                                                                               |
| `01_build_master.ipynb`              | สร้างตาราง + **ตรวจสอบ** (quality flag, H แยก phase, กราฟอุณหภูมิ, การผูก lab)                                                                              |
| `02_analysis.ipynb`                  | วิเคราะห์ เรียงตาม `workflow.md`: baseline → Step 1–4 → เชื่อมกับ lab                                                                                                    |
| `workflow.md`                        | แผนการวิเคราะห์ (เขียนโดยเจ้าของโปรเจกต์)                                                                                                                         |
| `archive/digester_analysis_v1.ipynb` | notebook เวอร์ชันแรก เก็บไว้ดูอ้างอิง **รันไม่ได้แล้ว** (ฟังก์ชันเปลี่ยนชื่อไปแล้ว)                                              |
| `data/`                              | ข้อมูลทั้งหมด (git ไม่เก็บ)                                                                                                                                                         |

---

## 4. Batch และ phase ถูกแบ่งยังไง

- ใช้ tag `Dk_main_sequence` (เช่น `PM2.104DIG1MAINSEQ`) ซึ่งบอก phase ปัจจุบันเป็นข้อความ
- ลำดับ phase: **CHIP FILLING → PREHYDRAU → HOT LIQUOR FILLING → HEAT&COOK → DISPLACEMENT → DISCHARGE → WAIT**
- **Batch ใหม่เริ่มทุกครั้งที่เข้า CHIP FILLING** (`batch_id` นับ 1, 2, 3, … แยกแต่ละหม้อ)
- `batch_number` คือเลข batch ของ DCS (`COOKNO.CALC`) เก็บไว้อ้างอิง
- ถ้า phase เดียวกันขึ้นซ้ำใน batch (เช่นถูก "8" ตัดกลาง) จะใช้เวลาเริ่มแรกสุด เวลาจบหลังสุด และนาทีรวมกัน
- ข้อความที่ไม่ใช่ phase จริง (เช่น "8", "0" = สถานะระบบของ PI) **ไม่นับเป็น phase** แต่นับไว้ใน `unknown_phase_count`

---

## 5. H-factor: หลักการ และ phase ที่ใช้

**หลักการ (Vroom):** อัตราการกำจัด lignin เพิ่มเร็วมากตามอุณหภูมิ H-factor รวม "อุณหภูมิ × เวลา" เป็นตัวเลขเดียว

```
relative rate  k(T) = exp(43.2 − 16115 / T_kelvin)      (100 °C = 1, 160 °C ≈ 400)
H-factor           = Σ k(T) × ชั่วโมง                  (รวมทุก step 5 นาที)
```

**อุณหภูมิที่ใช้:** `circulation_temp` (D1 = `PM2.104TI123`, D2 = `TI223`, D3 = `TI323`, D4 = `PM2.404TI423` ⚠️)

**Phase ที่ใช้ (`config.H_FACTOR_PHASES`):** HOT LIQUOR FILLING + HEAT&COOK + DISPLACEMENT

ทำไมไม่ใช้แค่ HEAT&COOK: ตรวจข้อมูล Aug–Sep 2026 แล้วพบว่า (ดู `01_build_master.ipynb` section 4–5)

|    | H ใน HOT LIQUOR FILLING | H ใน HEAT&COOK | H ใน DISPLACEMENT | HEAT&COOK คิดเป็น % ของทั้งหมด |
| -- | ------------------------- | ---------------- | ------------------- | ----------------------------------------------- |
| D1 | 247                       | 157              | 86                  | 31%                                             |
| D2 | 66                        | 167              | 94                  | 50%                                             |
| D3 | 46                        | 168              | 77                  | 57%                                             |

- ช่วง HOT LIQUOR FILLING อุณหภูมิขึ้นไป 130–165 °C แล้ว (เติม liquor ร้อน)
- ช่วง DISPLACEMENT ยังร้อน ~157 °C เกือบตลอด แล้วค่อยลด
- ช่วง PREHYDRAU **ใช้ circulation temp ไม่ได้**: pressure ขึ้น 7–9 bar แต่ circulation temp ค้าง ~85 °C (ไม่มีการไหลเวียน) ส่วน P-factor ใช้ค่าจาก DCS แทน

**Column ที่ได้:** `h_factor` (รวม 3 phase) และ `h_<phase>` ของทุก phase เช่น `h_heat_and_cook` สำหรับเทียบ ถ้าต้องการกลับไปใช้แค่ HEAT&COOK ให้แก้ `H_FACTOR_PHASES` ใน config

**วิธีคำนวณ:** คิด H ทีละ step ตลอดทั้งช่วงเวลาครั้งเดียว แล้วแบ่ง step เข้า phase ที่มันอยู่ จึงไม่มี step ตกหล่นระหว่าง phase (เวอร์ชันแรกตก step แรกของแต่ละ phase ไป ประมาณ 14% ของ HEAT&COOK)

### ⚠️ H-factor ไม่รู้น้ำหนัก chip

H-factor คิดจาก **อุณหภูมิ × เวลา อย่างเดียว** ถ้า 2 batch ต้มที่อุณหภูมิและเวลาเท่ากัน จะได้ H เท่ากัน แม้ batch หนึ่งมี chip 80 ตัน อีก batch 100 ตัน

แต่น้ำหนัก chip **ไม่คงที่** (SD 5–7 ตันต่อหม้อ, D3 ต่ำสุด 60 ตัน) ขณะที่ white liquor เติมเกือบคงที่ (median 12.86 m³ ทุกหม้อ) → batch ที่ chip น้อยได้ **alkali ต่อตันมากกว่า** และน่าจะ cook ลึกกว่า (Kappa ต่ำกว่า) ทั้งที่ H เท่ากัน

ผลคือ:
- H-factor อย่างเดียวอธิบาย Kappa ไม่ได้ (เห็นแล้ว: Spearman ≈ 0) ต้องดู **คู่กับ** alkali ต่อตัน chip
- เทียบ H-factor ข้ามหม้อที่ขนาดต่างกัน (D4 ถังใหม่) ไม่ได้ตรง ๆ

**คอลัมน์ที่เพิ่ม:** `white_liquor_m3` (= WL flow เฉลี่ย × เวลา HOT LIQUOR FILLING) และ `white_liquor_per_ton_chip` (÷ น้ำหนัก chip เปียก) ดูกราฟใน `02_analysis.ipynb` หัวข้อ "White liquor per ton of chips vs Kappa"

**สิ่งที่ต้องทำต่อ:**
1. ถามทีม process: เติม white liquor แบบปริมาตรคงที่ หรือปรับตามน้ำหนัก chip? (ข้อมูลบอกว่าแทบไม่ปรับ: Spearman WL m³ กับ chip = −0.01 ถึง +0.37)
2. ยืนยันว่า `PM2.104FIC532` (WL dosing, tag ใช้ร่วม) วัด WL ที่เข้าหม้อที่กำลังเติมจริง และหน่วย m³/h
3. หาความชื้น chip ที่ใช้ได้ (`MI801` ค้าง 35) เพื่อเปลี่ยนเป็นน้ำหนักแห้ง (BDt)
4. รู้ว่า g/l ใน accumulator เป็น EA หรือ AA → คำนวณ **alkali charge % ต่อไม้แห้ง** ได้จริง (ตัวแปรมาตรฐานของการต้ม)
5. ถ้าข้อ 1–4 ได้ ลองดู Kappa เทียบ **H-factor + alkali charge** พร้อมกัน (เช่น แบ่งกลุ่ม alkali charge แล้วดู H ในแต่ละกลุ่ม)
6. ยืนยันด้วยข้อมูลช่วงยาวขึ้น (Jun–Oct) เพราะความสัมพันธ์ตอนนี้ยังอ่อน

---

## 6. ผูก Lab เข้า batch ยังไง (เรื่อง lag time)

```
Lab ที่ Press 1 เวลา t
   └─► digester k  (ใช้ Dk_press1_status == k พอดี และมีใบเดียวที่ตรง)
          └─► batch ล่าสุดของหม้อ k ที่เริ่ม DISCHARGE ก่อนเวลา t (ไม่เกิน 12 ชม.)
```

- **Status tag ถูก PI AF lag มาแล้ว** (ช่วงถังระบาย 800 m³ + LC chest + 5 นาที, ดู `Pteam/Lag_Time_Sequence.md`) จึงไม่ต้องเลื่อนเวลา sensor รอบหม้อเอง **batch ทำหน้าที่เป็น lag**
- Sensor รอบหม้อถูกสรุปตาม phase ของ batch นั้น แล้วไปคู่กับ lab ของ batch นั้นโดยอัตโนมัติ
- Tag ที่ใช้ร่วมกันหลายหม้อ (เช่น alkali ใน accumulator) อ่าน**เฉพาะช่วงที่หม้อนั้นอยู่ใน phase นั้น**
- ถ้า batch มี lab หลาย sample ใช้ค่าเฉลี่ย (`press1_kappa`) และบอกจำนวนไว้ (`press1_kappa_samples`)
- Lab วัด Kappa ทุก 4 ชม. แต่ batch ออกทุก ~1–1.5 ชม. → **ประมาณ 1 ใน 3 ของ batch ที่มีค่า Kappa**

---

## 7. ตาราง `batch_master.csv`: ความหมายของ column

| กลุ่ม                        | Column                                                                                                                                            | ความหมาย                                                                                                                                         |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ID                                | `digester`, `batch_id`, `batch_number`                                                                                                      | หม้อ, ลำดับ batch (นับเอง), เลข batch ของ DCS                                                                                       |
| เวลา batch                    | `batch_start`, `batch_end`, `batch_hours`                                                                                                   | เริ่ม CHIP FILLING ถึงจบ phase สุดท้ายก่อน batch ถัดไป                                                                         |
| เวลาแต่ละ phase          | `<phase>_start`, `<phase>_end`, `<phase>_minutes`                                                                                           | phase = chip_filling, prehydrolysis, hot_liquor_filling, heat_and_cook, displacement, discharge, wait                                                    |
|                                   | `unknown_phase_count`                                                                                                                           | จำนวนช่วงที่ phase เป็นข้อความแปลก ("8", "0")                                                                                 |
| H-factor                          | `h_factor`                                                                                                                                      | รวม phase ใน `H_FACTOR_PHASES`                                                                                                                    |
|                                   | `h_<phase>`                                                                                                                                     | H ของแต่ละ phase (ไว้เทียบ)                                                                                                              |
| Feature (Step 1)                  | `chip_weight_max_chip_filling`                                                                                                                  | น้ำหนัก chip ที่โหลด (ตัน, น้ำหนักเปียก)                                                                                    |
|                                   | `ventilation_temp_max_chip_filling`                                                                                                             | อุณหภูมิ ventilation สูงสุดช่วงเติม chip                                                                                           |
|                                   | `liquor_to_wood_ratio`                                                                                                                          | (น้ำหนักหลังเติม liquor − น้ำหนัก chip) ÷ น้ำหนัก chip ≈ L:W (ใช้น้ำหนักเปียก เป็นค่าประมาณ) |
| Feature (Step 2)                  | `pfactor_actual_last_prehydrolysis`, `pfactor_setpoint_last_prehydrolysis`, `pfactor_gap`                                                   | P-factor ที่ได้, setpoint, ส่วนต่าง (actual − SP)                                                                                         |
|                                   | `digester_pressure_max_prehydrolysis`                                                                                                           | pressure สูงสุดช่วง prehydrolysis                                                                                                              |
| Feature (ช่วงเติม liquor) | `chip_weight_max_hot_liquor_filling`, `circulation_temp_max_hot_liquor_filling`                                                               | น้ำหนักหลังเติม liquor, อุณหภูมิสูงสุด                                                                                      |
|                                   | `white_liquor_dosing_flow_mean_…`, `alkali_accumulator1/2_conc_mean_…`                                                                      | tag ใช้ร่วม: WL dosing flow, ความเข้มข้น alkali (g/l) ช่วงที่หม้อนี้เติม liquor                                      |
|                                   | `white_liquor_m3`, `white_liquor_per_ton_chip`                                                                                                | WL ที่เติมใน batch (m³) และต่อตัน chip เปียก (m³/t) — ดูข้อ 5 "H-factor ไม่รู้น้ำหนัก chip"                       |
| Feature (Step 3)                  | `circulation_temp_max/mean_heat_and_cook`, `bottom_circulation_temp_mean_…`, `digester_pressure_mean_…`, `steam_to_heater_flow_mean_…` | อุณหภูมิ, pressure, ไอน้ำ ช่วง HEAT&COOK                                                                                                |
|                                   | `screen_diff_pressure_mean_…`, `circulation_pump_current_mean_…`                                                                            | สุขภาพการไหลเวียน (screen ตัน / ปั๊ม) — D4 ไม่มี screen ΔP                                                                |
| Feature (Step 4)                  | `displacement_liquor_temp_mean_displacement`, `black_liquor_conductivity_mean_displacement`                                                   | อุณหภูมิ displacement liquor, BL conductivity (proxy residual alkali, tag ใช้ร่วม)                                                        |
| Lab                               | `press1_kappa`, `press1_viscosity`, `press1_brightness`                                                                                     | ค่าเฉลี่ยของ sample จริงที่ผูกกับ batch นี้ (ว่าง = ไม่มี sample)                                                   |
|                                   | `press1_<…>_samples`, `press1_<…>_first_time`                                                                                               | จำนวน sample, เวลา sample แรก                                                                                                                |
| คุณภาพข้อมูล          | `quality_flag`                                                                                                                                  | `ok` หรือ flag (ดูข้อ 8)                                                                                                                      |

ชื่อ feature อ่านว่า **`<sensor>_<สถิติ>_<phase>`** เช่น `circulation_temp_max_heat_and_cook` = อุณหภูมิ circulation สูงสุดช่วง HEAT&COOK

**เพิ่ม feature ใหม่:** เพิ่มหนึ่งบรรทัดใน `BATCH_FEATURES` ใน `config.py` เช่น

```python
("digester_pressure", ["DISPLACEMENT"], "mean"),   # -> digester_pressure_mean_displacement
```

แล้วรัน `01_build_master.ipynb` ใหม่ (sensor ต้องมีอยู่ใน config และในข้อมูลที่ pull มา)

---

## 8. Quality flag (ไม่ลบข้อมูล แค่ติดป้าย)

| Flag              | ความหมาย                               | ตัวอย่างที่เจอ                                                                                         |
| ----------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `ok`            | batch ปกติ                                 | 904 จาก 949 batch (Aug–Sep)                                                                                      |
| `missing_phase` | ไม่มี HEAT&COOK หรือ DISCHARGE        | sequence สะดุด (CHIP FILLING แล้วกระโดดไป WAIT), batch ถูกตัดที่ขอบช่วงข้อมูล |
| `unknown_phase` | มี phase "8"/"0"                             | สถานะระบบของ PI แทรก                                                                                 |
| `long_batch`    | ยาวเกิน `LONG_BATCH_HOURS` (12 ชม.) | มีการหยุดเครื่อง (เช่น D4 WAIT 28 ชม.)                                                         |
| `no_h_factor`   | H-factor ว่างหรือ 0                    |                                                                                                                      |

`02_analysis.ipynb` ใช้เฉพาะ `ok` (ตั้ง `ONLY_OK_BATCHES = False` ถ้าต้องการดูทั้งหมด)

---

## 9. ผลที่เจอแล้ว (Aug–Sep 2026, batch `ok`)

- **H-factor ไม่สัมพันธ์กับ Kappa** ทั้งแบบใหม่ (3 phase) และแบบ HEAT&COOK อย่างเดียว (Spearman ≈ 0 ทุกหม้อ) ในช่วงที่ process เดินอยู่ ความต่างของ H ระหว่าง batch ยังไม่ใช่ตัวกำหนด Kappa หลัก (หรือถูกกลบด้วยตัวแปรอื่น หรือการผสมในถังระบาย)
- **P-factor สูง → Kappa สูง** เห็นซ้ำใน D1–D3 (D2: r = +0.34, p < 0.01) เป็นไปได้ทางฟิสิกส์ (prehydrolysis แรงทำให้ lignin condense แล้ว cook ออกยากขึ้น) **น่าตามต่อที่สุด**
- ความเข้มข้น alkali ใน accumulator สัมพันธ์กับ Kappa ทางบวก (D1 +0.31, D2 +0.30) ซึ่งขัดกับที่คาด ต้องเช็คว่า tag วัดอะไรจริงและมี trend ตามเวลาปนอยู่ไหม
- **White liquor ต่อตัน chip สูง → Kappa ต่ำ** ทิศเดียวกันทั้ง 4 หม้อ (Spearman −0.12 ถึง −0.19) ตรงกับเคมี แต่ยังอ่อน ต้องยืนยันด้วยข้อมูลมากขึ้น อุณหภูมิ cook เท่ากันทุกหม้อ (~157–159 °C) แต่น้ำหนัก chip ต่างกัน (D4 72 ตัน, D1–D3 87–95 ตัน) ดูข้อ 5
- ทุกค่าเป็น **ความสัมพันธ์ ไม่ใช่เหตุผล** และทดสอบหลายตัวพร้อมกัน ค่า |r| < 0.25 ควรถือเป็น noise

---

## 10. ข้อจำกัด / สิ่งที่ต้องยืนยัน

| เรื่อง                                                                                                                       | ผลกระทบ                                                      | ต้องทำ                                              |
| ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------- |
| **D4 temperature tag** (`TI423` หรือ `TI418`) พฤติกรรมไม่เหมือน D1–D3 (H สูงช่วง PREHYDRAU) | H-factor ของ D4 เทียบตรงกับใบอื่นไม่ได้   | ถามทีม process ว่าวัดจุดไหน             |
| **D4 เป็นถังใหม่** ไม่แน่ใจว่าปริมาตรเท่า D1–D3 ไหม (chip ต่อ batch D4 ≈ 72 ตัน vs D1–D3 87–95 ตัน, steam to heater D4 ≈ 20 vs 1–3) | เทียบค่าที่ขึ้นกับขนาดถัง (น้ำหนัก, flow, L:W) ข้าม D4 กับใบอื่นตรง ๆ ไม่ได้ | ถามปริมาตรถัง D4 และ D1–D3 จากทีม process |
| ความชื้น chip (`MI801`) ค่าค้าง 35                                                                                | รู้แค่น้ำหนักเปียก L:W เป็นค่าประมาณ | –                                                        |
| EA ต่อหม้อ (`AI446` ของ D4) = 0                                                                                        | ไม่รู้ alkali charge จริงต่อหม้อ                   | ถามว่า g/l ใน accumulator เป็น EA หรือ AA |
| SOP (Kappa 7.5–8.5, Visc 680–710, Bright 37–40)                                                                                 | ข้อมูลเกือบทั้งหมดอยู่นอก SOP              | ยืนยันกับทีม process                          |
| เยื่อจากหลาย batch ผสมกันในถังระบาย 800 m³                                                            | สัญญาณของแต่ละ batch เจือจาง                   | ข้อจำกัดของวิธี                            |
| Lab noise ~±0.37 Kappa, ~60–85 batch ต่อหม้อ                                                                              | ความต่างเล็ก ๆ อาจเป็น noise                    | –                                                        |

---

## 11. แก้ปัญหาที่เจอบ่อย

| อาการ                                                               | สาเหตุ                                                 | แก้                                                                                                                                                           |
| ------------------------------------------------------------------------ | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `FileNotFoundError: … digester_….csv.gz`                             | ยังไม่ได้ pull หรือไฟล์อยู่ผิดที่ | รัน `python pull_data.py` (ไฟล์จะไปที่ `data/` ข้างไฟล์นี้เสมอ) ไฟล์ที่แตก zip แล้ว (`.csv`) ก็อ่านได้ |
| `FileNotFoundError: … batch_master.csv` ใน 02                       | ยังไม่ได้รัน 01                                  | รัน `01_build_master.ipynb` ก่อน                                                                                                                        |
| `ImportError: cannot import name …`                                   | kernel จำ `.py` เวอร์ชันเก่า                 | รัน cell แรกใหม่ (มี autoreload) หรือ Restart Kernel                                                                                             |
| ช่วงเวลาใหม่แต่ notebook ยังใช้ข้อมูลเก่า | ชื่อไฟล์มาจาก `START_TIME`/`END_TIME`       | ตรวจ config ให้ตรงกับไฟล์ที่ pull                                                                                                            |
