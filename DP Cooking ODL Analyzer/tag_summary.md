# สรุปรายละเอียด Tags และ พารามิเตอร์ทั้งหมดในโปรเจกต์ (Tag Summary Reference)

เอกสารฉบับนี้รวบรวม **PI Tags** ทั้งหมดที่ใช้ในโปรเจกต์ **DP Cooking ODL Analyzer (Pulp Line 2)** ได้แก่ ผลแล็บ QA, เซนเซอร์การผลิต DCS, สถานะ Batch จาก PI AF และค่าที่คำนวณเพิ่ม

> **PI Server:** `\\VPKGDRBPPI01` · **PI AF:** `\\VPKGDCIPS01\iPMS` → element `PPPC_DP_Cooking`
> **ที่มาของชื่อ Tag:** `Doc/PPPC Line 2 ODL Tag 1.pptx`, `Doc/formula DP.pptx`, `onedrive_to_pi/config.py`, `Lab_Analysis/realtime_pi_press1_analysis.ipynb`
> **ปรับปรุงล่าสุด:** 2026-10-12

---

## หมวดที่ 1: QA Lab Quality Tags (19 PI Tags จาก OneDrive Logbook)

ผลแล็บวัดคุณภาพเยื่อ ดึงมาจาก Excel Log Book บน SharePoint แล้วส่งเข้า PI ผ่าน `onedrive_to_pi` (gateway `write_old`) โดยใช้ timestamp ตามเวลาเก็บตัวอย่างจริง
ความถี่การวัดจริง: **Kappa และ Viscosity ทุก 4 ชม.** · **Brightness ทุก 2 ชม.**

> ⚠️ D0 / D1 / D2 ในหมวดนี้คือ **ทาวเวอร์ฟอก (Bleaching)** ไม่ใช่หม้อต้ม D1–D4

| # | Field Name | PI Tag | คอลัมน์ Excel | จุดวัด | ความหมาย |
|---|---|---|---|---|---|
| **Kappa Number** (ดัชนีลิกนินที่เหลือในเยื่อ) | | | | | |
| 1 | `Kappa_Press1` | `PULP-LINE2-KAPPA-PRESS1` | Col F (5) | Press 1 | Kappa หลังต้ม ก่อนเข้า ODL |
| 2 | `Kappa_Press3` | `PULP-LINE2-KAPPA-PRESS3` | Col G (6) | Press 3 | Kappa หลัง ODL |
| 3 | `Kappa_Eop` | `PULP-LINE2-KAPPA-EOP` | Col H (7) | EOP Tower | Kappa หลังทาวเวอร์ EOP |
| **Viscosity** (ความหนืด, cm³/g) | | | | | |
| 4 | `Viscosity_Press1` | `PULP-LINE2-VISCOSITY-PRESS1` | Col I (8) | Press 1 | ความหนืดที่ Press 1 |
| 5 | `Viscosity_Press3` | `PULP-LINE2-VISCOSITY-PRESS3` | Col J (9) | Press 3 | ความหนืดที่ Press 3 |
| 6 | `Viscosity_D0` | `PULP-LINE2-VISCOSITY-D0` | Col K (10) | D0 Tower | ความหนืดที่ทาวเวอร์ D0 |
| 7 | `Viscosity_Eop` | `PULP-LINE2-VISCOSITY-EOP` | Col L (11) | EOP Tower | ความหนืดที่ทาวเวอร์ EOP |
| 8 | `Viscosity_D1` | `PULP-LINE2-VISCOSITY-D1` | Col M (12) | D1 Tower | ความหนืดที่ทาวเวอร์ D1 |
| 9 | `Viscosity_D2` | `PULP-LINE2-VISCOSITY-D2` | Col N (13) | D2 Tower | ความหนืดที่ทาวเวอร์ D2 |
| **Brightness** (ความสว่าง, %) | | | | | |
| 10 | `Brightness_Press1` | `PULP-LINE2-BRIGHTNESS-PRESS1` | Col P (15) | Press 1 | ความสว่างที่ Press 1 |
| 11 | `Brightness_Press3` | `PULP-LINE2-BRIGHTNESS-PRESS3` | Col Q (16) | Press 3 | ความสว่างที่ Press 3 |
| 12 | `Brightness_D0` | `PULP-LINE2-BRIGHTNESS-D0` | Col R (17) | D0 Tower | ความสว่างที่ทาวเวอร์ D0 |
| 13 | `Brightness_Eop` | `PULP-LINE2-BRIGHTNESS-EOP` | Col S (18) | EOP Tower | ความสว่างที่ทาวเวอร์ EOP |
| 14 | `Brightness_D1` | `PULP-LINE2-BRIGHTNESS-D1` | Col T (19) | D1 Tower | ความสว่างที่ทาวเวอร์ D1 |
| 15 | `Brightness_D2` | `PULP-LINE2-BRIGHTNESS-D2` | Col V (21) | D2 Tower | ความสว่างที่ทาวเวอร์ D2 |
| **pH** | | | | | |
| 16 | `pH_D0` | `PULP-LINE2-PH-D0` | Col AA (26) | D0 Tower | pH ที่ทาวเวอร์ D0 |
| 17 | `pH_Eop` | `PULP-LINE2-PH-EOP` | Col AB (27) | EOP Tower | pH ที่ทาวเวอร์ EOP |
| 18 | `pH_D1` | `PULP-LINE2-PH-D1` | Col AC (28) | D1 Tower | pH ที่ทาวเวอร์ D1 |
| 19 | `pH_D2` | `PULP-LINE2-PH-D2` | Col AD (29) | D2 Tower | pH ที่ทาวเวอร์ D2 |

**SOP ที่ notebook ใช้ (ยังรอยืนยันจากทีม process):** Kappa 7.5–8.5 · Viscosity 680–710 · Brightness 37–40
**Spike filter ใน notebook:** Viscosity 400–2000 · Brightness 25–50

---

## หมวดที่ 2: Steam (ไอน้ำ) — สรุปแยก

| ประเภท | PI Tag | หน่วย | จุดใช้งาน | สถานะในโปรเจกต์ |
|---|---|---|---|---|
| **MP Steam** (Medium Pressure) | `PM2.305FIC036:MV` | t/h | Pulp heater ก่อนเข้า ODL Reactor 2 (คุมอุณหภูมิ `PM2.105TIC322:MV`) | ✅ ใช้ใน notebook และ Pteam |
| **LP Steam** (Low Pressure) | — ยังไม่มีในโปรเจกต์ — | t/h | — | ❌ ไม่พบใน code, DCS export หรือเอกสาร tag |
| Steam ฝั่งหม้อต้ม (D1–D4) | — ยังไม่มีในโปรเจกต์ — | — | การให้ความร้อนในหม้อต้ม | ❌ ไม่พบ |

> ถ้าต้องการวิเคราะห์ LP Steam หรือ steam ของหม้อต้ม ต้องขอชื่อ tag จากทีม DCS/process ก่อน แล้วค่อยเพิ่มเข้า `TAGS` ใน notebook และคำนวณ Specific consumption แบบเดียวกับ MP Steam

---

## หมวดที่ 3: Process Sensor Parameters (DCS Tags จาก PI)

ชื่อพารามิเตอร์ตรงกับหัวคอลัมน์ในไฟล์ DCS export (`Pteam/df_imported_PPPC_DPCooking.xlsx`) · คอลัมน์ **ใช้ใน**: **NB** = notebook ปัจจุบัน, **PT** = Pteam
ช่อง PI Tag ที่เขียนว่า *ไม่ระบุ* หมายถึงยังไม่พบชื่อ tag ในเอกสาร (มีแค่ชื่อคอลัมน์ใน Excel export)

### 3.1 กำลังการผลิตและการไหล (Production & Slurry Flow)

| Parameter | PI Tag | หน่วย | ใช้ใน | ความหมาย |
|---|---|---|---|---|
| `Production ODL (ADT/D)` | `PM2.Prod.ODL` | ADT/D | NB, PT | อัตราการผลิตเยื่อ ODL (ตัวหารของ Specific consumption ทุกตัว) |
| `Deknotting Feed Flow (m3/h)` | `PM2.106FIC006:MV` | m³/h | NB, PT | flow เข้าเครื่องคัดปมไม้ (ใช้เป็น FlowPress1 ในสูตร lag ด้วย) |
| `Deknotting Feed Cons (%)` | *ไม่ระบุ* | % | PT | consistency เข้าเครื่องคัดปมไม้ |
| `Screening Accept flow (m3/h)` | *ไม่ระบุ* | m³/h | PT | flow เยื่อดีที่ผ่าน Screening |
| `Press 1 Feed Cons (%)` | `PM2.105NIC207:MV` | % | NB, PT | consistency เข้า Press 1 |
| `Press 2 Feed Cons (%)` | *ไม่ระบุ* | % | PT | consistency เข้า Press 2 |
| `Press 3 Feed Cons (%)` | *ไม่ระบุ* | % | PT | consistency เข้า Press 3 |
| `Press 1 Dilute Screen (m3/h)` | *ไม่ระบุ* | m³/h | PT | น้ำเจือจางเข้า Press 1 |
| `Press 2 Dilute Screen (m3/h)` | *ไม่ระบุ* | m³/h | PT | น้ำเจือจางเข้า Press 2 |
| `Press 3 Dilute Screen (m3/h)` | *ไม่ระบุ* | m³/h | PT | น้ำเจือจางเข้า Press 3 |

**Flow tag อื่นที่อยู่ในเอกสาร `formula DP.pptx`** (ยังไม่ได้ใช้ใน analysis)

| PI Tag | ความหมาย |
|---|---|
| `PM2.105FIC208:MV`, `PM2.105FIC238:MV` | Standpipe outlet flow → `Standpipe_Outlet_Flow = (FIC208 + FIC238) × (NIC207/100) / 0.12` |
| `PM2.105FIC444:MV`, `PM2.105FIC408:MV` | Blow tank outlet flow → `BlowTank_Outlet_Flow = FIC444 + FIC408` |
| `PM2.105FIC544:MV`, `PM2.105FIC508:MV` | อยู่ในสไลด์เดียวกับปริมาตรถัง ODL/LC chest แต่**ไม่มีคำอธิบาย** (คาดว่าเป็น flow ของ LC chest — ต้องยืนยัน) |

### 3.2 สารเคมีและไอน้ำ (Chemicals & Steam Feed)

| Parameter | PI Tag | หน่วย | ใช้ใน | ความหมาย |
|---|---|---|---|---|
| `WHLiqu to DilSrew_White liquor (m3/h)` | `PM2.105FIC303:MV` | m³/h | NB, PT | น้ำยาขาว (NaOH + Na₂S) เข้าสกรูเจือจาง |
| `MP Steam Pulp Heat_Feed before Reactor 2 (t/h)` | `PM2.305FIC036:MV` | t/h | NB, PT | ไอน้ำ MP อุ่นเยื่อก่อนเข้า ODL Reactor 2 |
| `O2 to Mixer1_Oxygen feed at Reactor 1 (kg/h)` | `PM2.305FIC019:MV` | kg/h | PT | ออกซิเจนเข้า Mixer 1 ก่อน Reactor 1 |
| `O2 to pulp heater_Oxygen feed at Reactor 2 (kg/h)` | `PM2.305FIC022:MV` | kg/h | PT | ออกซิเจนเข้า Pulp Heater ก่อน Reactor 2 |

### 3.3 อุณหภูมิและความดัน ODL (Temperature & Pressure)

| Parameter | PI Tag | หน่วย | ความหมาย |
|---|---|---|---|
| `O2_Oxygen pressure (bar)` | `PM2.305PI017` | bar | ความดันออกซิเจนหลักเข้าไลน์ ODL |
| `O2-line_Temp Oxygen to ODL (oC)` | `PM2.105TI318` | °C | อุณหภูมิออกซิเจนเข้าไลน์ ODL |
| `O2 REACT PRESS.CTRL._Pressure at Reactor 1 (bar)` | `PM2.305PIC023:MV` | bar | loop ควบคุมความดัน Reactor 1 |
| `O2 Reactor1_Pressure at Reactor 1 (bar)` | `PM2.305PIC030:MV` | bar | ความดัน Reactor 1 |
| `O2 Reactor1 TOP_Pressure top Reactor 1_1 (bar)` | `PM2.305PZ024` | bar | ความดันยอด Reactor 1 (จุดที่ 1) |
| `O2 Reactor1 TOP_Pressure top Reactor 1_2 (bar)` | `PM2.305PZ025` | bar | ความดันยอด Reactor 1 (จุดที่ 2) |
| `Oxygen Reactor_Pressure top Reactor 1 (bar)` | `PM2.105PS328` | bar | ความดันยอด Oxygen Reactor |
| `O2 Reactor1 TOP_Temp top Reactor 1 (oC)` | `PM2.305TI026` | °C | อุณหภูมิยอด Reactor 1 |
| `O2 Reactor1 Bottom_Temp bottom Reactor 1 (oC)` | `PM2.305TI028` | °C | อุณหภูมิท้าย Reactor 1 |
| `O2 Reactor FeedTemp_Pulp temp feed Reactor 2 (oC)` | `PM2.105TIC322:MV` | °C | อุณหภูมิเยื่อก่อนเข้า Reactor 2 (ตัวที่ MP Steam คุม) |
| `Oxygen Reactor_Temp top Reactor 2 (oC)` | `PM2.105TI326` | °C | อุณหภูมิยอด Reactor 2 |

> ในข้อมูล 2026-03-01 → 2026-06-15 (30,529 แถว) ค่า `PIC023` กับ `PIC030` เท่ากัน 99% ของจุด และสไลด์ 1 ของ tag deck ไม่มี `PIC023` (มีแต่สไลด์ 2) ควรยืนยันว่าเป็น tag คนละตัวจริง

### 3.4 Online Kappa (มีใน export แต่ใช้ไม่ได้)

| Parameter | PI Tag | หน่วย | หมายเหตุ |
|---|---|---|---|
| `Pre O2 Kappa_Kappa online (%)` | `PM2.105KI002` | – | ค่าเป็น 0 ทั้งหมด (เซนเซอร์ไม่ทำงาน) |
| `Post O2 Kappa_Kappa online (%)` | `PM2.105KI003` | – | ค่าเป็น 0 ทั้งหมด (เซนเซอร์ไม่ทำงาน) |

---

## หมวดที่ 4: Specific Consumption (คำนวณเพิ่ม)

สูตร: `24 × Flow / PM2.Prod.ODL` และถ้า Production ≤ 0 ให้เป็น NaN (กันหารด้วยศูนย์)
ค่านี้พุ่งแบบ 1/x ตอนผลิตช้าหรือหยุด เพราะ feed ยังเดินอยู่ — เป็นตัวแยก batch Abnormal ที่แรงที่สุด

| Parameter | สูตร (PI Tag) | หน่วย | ใช้ใน |
|---|---|---|---|
| `Specific Steam Consumption (t_ADT)` | `24 × PM2.305FIC036:MV / PM2.Prod.ODL` | t/ADT | NB, PT |
| `Specific WHLiqu Consumption (m3_ADT)` | `24 × PM2.105FIC303:MV / PM2.Prod.ODL` | m³/ADT | NB, PT |
| `Specific O2 Mixer 1 Consumption (kg_ADT)` | `24 × PM2.305FIC019:MV / PM2.Prod.ODL` | kg/ADT | PT |
| `Specific O2 Pulp Heater Consumption (kg_ADT)` | `24 × PM2.305FIC022:MV / PM2.Prod.ODL` | kg/ADT | PT |

---

## หมวดที่ 5: Batch Status Tags (จาก PI AF `PPPC_DP_Cooking`)

รายละเอียดสูตรทั้ง 9 ขั้นอยู่ใน `Pteam/Lag_Time_Sequence.md`

### 5.1 ที่ใช้งานอยู่

| PI Tag | ค่า | ใช้ใน | ความหมาย |
|---|---|---|---|
| `PPPC_DP_Cooking.B1_Discharge_FinalTime_Press1_Status` … `B4_…` | k หรือ 0 | NB | เยื่อของหม้อต้ม k อยู่ที่ Press 1 |
| `B1_DischargeStatus_FinalTime_Status_Rev`, `B2..B4_Discharge_FinalTime_Status` | k หรือ 0 | – | หม้อต้ม k ถือสถานะในถังระบาย 800 m³ (FIFO) |
| `Bn_Current_Sequence` | ข้อความ | – | ลำดับขั้นของหม้อต้ม (CHIP FILLING … DISCHARGE, WAIT) |
| `Dig1..4_Discharge_BatchStatus`, `Dig1..4_Press1_BatchStatus` | 0–4 | PT | ชื่อคอลัมน์สถานะใน DCS export ของ Pteam |

> ⚠️ PI เก็บ tag สถานะแบบ `Step = 0` และ AF ใช้ `InterpolatedValues` จึงมีค่าทศนิยม (เช่น 0.5, 1.95) ประมาณ 20% ของจุดที่บันทึก · notebook จึงนับเป็น Dk เฉพาะเมื่อ `Bk == k` พอดีเท่านั้น

### 5.2 ที่วางแผนไว้ (จาก `formula DP.pptx`)

| PI Tag | ความหมาย |
|---|---|
| `B{n}_ODL_Tank1_Status`, `ODL_Tank1_Retention_Time` | เยื่อของหม้อต้ม n อยู่ใน O2 Tank 1 |
| `B{n}_ODL_Tank2_Status`, `ODL_Tank2_Retension_Time` | เยื่อของหม้อต้ม n อยู่ใน O2 Tank 2 |
| `B{n}_LCChest_Tank1_Press2_Status`, `LCChest_Tank1_Retention_Time` | เยื่อของหม้อต้ม n ที่ Press 2 |
| `B{n}_LCChest_Tank2_Press3_Status`, `LCChest_Tank2_Retention_Time` | เยื่อของหม้อต้ม n ที่ Press 3 |
| `PULP-LINE2-PRESS1-ACTIVE-DIGESTER` | หม้อต้มที่ active ที่ Press 1 (tag เดียว) |
| `PULP-LINE2-ODL1-ACTIVE-DIGESTER`, `PULP-LINE2-ODL2-ACTIVE-DIGESTER` | หม้อต้มที่ active ที่ ODL Tank 1 / 2 |
| `PULP-LINE2-LCCHEST1-ACTIVE-DIGESTER`, `PULP-LINE2-LCCHEST2-ACTIVE-DIGESTER` | หม้อต้มที่ active ที่ LC Chest 1 / 2 |

### 5.3 ปริมาตรถังที่ใช้คำนวณ lag (steady state: เวลา = ปริมาตร ÷ flow)

| ถัง | ปริมาตร |
|---|---|
| Discharge Tank | 800 m³ |
| O2 Tank 1 | 95 m³ |
| O2 Tank 2 | 145 m³ |
| LC Chest 1 | 110 m³ |
| LC Chest 2 | 125 m³ |
| รวม Press 1 → Press 3 (CapaTank3) | 475 m³ |

---

## หมวดที่ 6: โครงสร้างการไหลของข้อมูล (Data Flow)

```
[SharePoint Log Book (Excel)]
   └─ onedrive_to_pi: step0 download → step1 parse → step2 filter (3-day lookback) → step3 POST
         └─ write_old gateway (127.0.0.1:5707, AFSDK) ──▶ [AVEVA PI Server VPKGDRBPPI01] ◀── DCS sensors (PM2.*)
                                                                │        ▲
                                     PI AF (PPPC_DP_Cooking) ◀──┘        └── writes Bk_..._Press1_Status
                                                                │
                                    MI Cube API (InterpolatedValue/MultiTag)
                                                                ▼
                              Lab_Analysis/realtime_pi_press1_analysis.ipynb · PI Vision
```
