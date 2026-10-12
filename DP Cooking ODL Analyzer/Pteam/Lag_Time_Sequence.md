# Lag Time Sequence — การระบุหม้อต้ม (D1–D4) ของเยื่อที่ Press 1

> **ที่มา:** PI AF Analysis ใน `\\VPKGDCIPS01\iPMS` → element `PPPC_DP_Cooking` (PI Server `VPKGDRBPPI01`)
> **สถานะ:** Mapping ของ After Press 1 ครบแล้ว (2026-09-23) · ขั้นต่อไปคือ After Press 3
> **สมมติฐาน:** Flow เป็น **steady state** คำนวณเวลาอยู่ในถัง (retention time) จาก `ปริมาตร ÷ flow`

---

## 1. ภาพรวม

คำถามที่ต้องตอบคือ **เยื่อที่ Press 1 ณ เวลา t มาจากหม้อต้มใบไหน** วิธีคิดแบ่งเป็น 2 ส่วน:

1. หาช่วงเวลาที่เยื่อของ batch อยู่ในถังระบาย `[T_D, T_F]`
2. เลื่อนช่วงนั้นไปตามเวลาที่เยื่อใช้เดินทางจากถังถึง Press 1 (`τ_LC + 5 นาที`)

```
Press1_Status_Bn(t) = n   ถ้า ณ เวลา (t − τ_LC − 5 นาที) หม้อต้ม n ถือสถานะอยู่ในถัง
```

## 2. ลำดับการคำนวณ (ใช้หม้อต้ม 1 (B1) เป็นตัวอย่าง ส่วน B2–B4 ทำแบบเดียวกัน)

> **หลักของ PI AF:** `เวลา + ตัวเลข` ตัวเลขมีหน่วยเป็นวินาที (จึงต้อง ×60 จากนาที) และ `เวลา − เวลา` ได้ผลเป็นวินาที
> Output ที่แสดง **"Map"** คือตัวแปรกลาง ไม่ได้บันทึกลง PI จึงดึงค่าย้อนหลังไม่ได้

### Step 1: หาเวลาเริ่มระบาย (T_D)

|                            |                                                                                         |
| -------------------------- | --------------------------------------------------------------------------------------- |
| **Tag ที่ใช้** | `B1_Current_Sequence` (ข้อความ: CHIP FILLING, HOT LIQUOR, …, DISCHARGE, WAIT) |
| **ได้ค่า**     | `B1_Discharge_Timestamp` (ตัวแปรกลาง / Map)                                 |

```
IF BadVal(FindEq('B1_Current_Sequence','*-4h','*',"DISCHARGE")) Then '*' + 2000
ELSE FindEq('B1_Current_Sequence','*-4h','*',"DISCHARGE")
```

หาเวลาแรกในช่วง 4 ชม.ที่ผ่านมาที่ Sequence = DISCHARGE ถ้าหาไม่เจอ ใช้ `ตอนนี้ + 2000 วินาที (≈33 นาที)`

### Step 2: หาเวลาระบายเสร็จ (T_W)

|                            |                             |
| -------------------------- | --------------------------- |
| **Tag ที่ใช้** | `B1_Current_Sequence`     |
| **ได้ค่า**     | `B1_Wait_Timestamp` (Map) |

```
IF BadVal(FindEq('B1_Current_Sequence','*-4h','*',"WAIT")) Then '*' + 2000
ELSE FindEq('B1_Current_Sequence','*-4h','*',"WAIT")
```

ถ้ายังระบายอยู่ (ยังไม่เข้า WAIT) จะใช้ค่าแทน `'*'+2000` ผลคือ Step 3 และ Step 5 ยืดออกไปเรื่อย ๆ ตามเวลาปัจจุบัน

### Step 3: ระยะเวลาที่หม้อต้มระบาย

|                        |                                               |
| ---------------------- | --------------------------------------------- |
| **ใช้**       | T_D, T_W                                      |
| **ได้ค่า** | `B1_Discharge_Timeduration` (นาที, Map) |

```
IF Hour(B1_Wait_Timestamp) <> Hour(B1_Discharge_Timestamp)
  Then (60 + Minute(B1_Wait_Timestamp)) - Minute(B1_Discharge_Timestamp)
ELSE Minute(B1_Wait_Timestamp) - Minute(B1_Discharge_Timestamp)
```

### Step 4: เวลาที่ถังระบายจนหมด (τ_tank)

|                            |                                                                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Tag ที่ใช้** | `Maximum_Discharge_Level` (%), `Average_Total_Discharge_Flow` (m3/h) (ค่ารวมของถัง ไม่ได้แยกตามหม้อต้ม) |
| **ได้ค่า**     | Attribute`Time_Duration_Batch` (นาที)                                                                                                |

```
A=Average_Total_Discharge_Flow; B=Maximum_Discharge_Level; C=Flow_by_Slope_estimation;
[( ( ( (B/100)*800)/A )* 60 )]; UOM=min
```

ถังขนาด 800 m3 ส่วน `C` ถูกประกาศไว้แต่ **ไม่ได้ใช้** ในสูตร
ตัวอย่าง: ระดับ 50%, flow 391.75 m3/h → 0.5 × 800 / 391.75 × 60 ≈ **61 นาที**

### Step 5: เวลาที่เยื่อของ batch ออกจากถังหมด (T_F)

|                        |                                      |
| ---------------------- | ------------------------------------ |
| **ใช้**       | Step 1 + Step 3 + Step 4             |
| **ได้ค่า** | `B1Discharge_FinalTimestamp` (Map) |

```
B1_Discharge_Timestamp + ('Time_Duration_Batch'*60) + (B1_Discharge_Timeduration*60)
```

T_F = T_D + ระยะเวลาระบายจากหม้อต้ม + เวลาระบายถัง (เป็นคนละช่วงกัน ไม่ได้นับซ้ำ)

### Step 6: สถานะในถังว่าตอนนี้เป็นของหม้อต้มใบไหน (FIFO)

|                                              |                                                                                                                           |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **ใช้**                             | T_D, T_F ของ B1 ·`B2/B3/B4_Discharge_Timestamp` · สถานะรอบก่อน `B2/B3/B4_Discharge_FinalTime_Status` |
| **ได้ค่า (บันทึกลง PI)** | B1 →`B1_DischargeStatus_FinalTime_Status_Rev` (1/0)                                                                    |
|                                              | B2 →`B2_Discharge_FinalTime_Status` (2/0) · B3 → `B3_…` (3/0) · B4 → `B4_…` (4/0)                            |

```
IF
(('B2_Discharge_FinalTime_Status' = 2) AND (B2_Discharge_Timestamp > B1_Discharge_Timestamp) AND (B1_Discharge_Timestamp <= '*' AND B1Discharge_FinalTimestamp >= '*')) OR
(('B3_Discharge_FinalTime_Status' = 3) AND (B3_Discharge_Timestamp > B1_Discharge_Timestamp) AND (B1_Discharge_Timestamp <= '*' AND B1Discharge_FinalTimestamp >= '*')) OR
(('B4_Discharge_FinalTime_Status' = 4) AND (B4_Discharge_Timestamp > B1_Discharge_Timestamp) AND (B1_Discharge_Timestamp <= '*' AND B1Discharge_FinalTimestamp >= '*')) OR
(('B2_Discharge_FinalTime_Status' <> 2) AND ('B3_Discharge_FinalTime_Status' <> 3) AND ('B4_Discharge_FinalTime_Status' <> 4)) AND (B1_Discharge_Timestamp <= '*' AND B1Discharge_FinalTimestamp >= '*')
THEN 1
ELSE 0
```

**	เวลาปัจจุบัน (`'*'`)**

**B1 = 1 เมื่อครบทั้ง 2 ข้อ:**

1. ตอนนี้อยู่ในช่วงของ B1: `T_D1 ≤ ตอนนี้ ≤ T_F1`
2. ไม่มีหม้อต้มใบอื่นถือสถานะอยู่ **หรือ** ใบที่ถือสถานะอยู่เริ่มระบาย **หลัง** B1

**ความหมาย: FIFO** batch ที่ระบายก่อนถือสถานะไปจนถึง T_F ใบที่ระบายทีหลังต้องรอ ตรงกับการไหลแบบ plug flow ในถัง

| ตอนนี้ | B1 (เริ่ม 08:00, T_F 10:41)         | B3 (เริ่ม 09:50, T_F 12:30)             | ผล                                       |
| ------------ | ---------------------------------------- | -------------------------------------------- | ------------------------------------------ |
| 09:00        | อยู่ในช่วง                     | ยังไม่เริ่ม                       | **B1 = 1**                           |
| 10:00        | อยู่ในช่วง, ระบายก่อน | อยู่ในช่วง, ระบายทีหลัง | **B1 = 1**, B3 = 0 (รอ)            |
| 10:45        | หมดช่วง                           | อยู่ในช่วง                         | B1 = 0 → รอบถัดไป**B3 = 3** |

### Step 7: Lag จากถังถึง Press 1

|                            |                                                                                                 |
| -------------------------- | ----------------------------------------------------------------------------------------------- |
| **Tag ที่ใช้** | `4. LC Chest Outlet Flow (m3/h)`                                                              |
| **ได้ค่า**     | Attribute`LC Chest Retention Time` (นาที) → ตัวแปร `LCChest_RetentionTime` (Map) |

```
'LC Chest Retention Time':   A=4. LC Chest Outlet Flow (m3/h); [if A <= 0 then 0 else (125/A)*60]

LCChest_RetentionTime = '*'-(('LC Chest Retention Time'*60)+(5 *60))
```

ถัง LC Chest 125 m3 ÷ outlet flow แล้วบวก offset ตายตัว **5 นาที** ได้จุดเวลาที่ต้องย้อนกลับไปดู
ตัวอย่าง: τ_LC = 24 นาที → ย้อนหลัง **29 นาที**

### Step 8: สถานะที่ Press 1

|                                              |                                                                 |
| -------------------------------------------- | --------------------------------------------------------------- |
| **Tag ที่ใช้**                   | `B1_DischargeStatus_FinalTime_Status_Rev` (ผลจาก Step 6) |
| **ได้ค่า (บันทึกลง PI)** | `B1_DischargeStatus_FinalTime_Press1_Status`                  |

```
FirstValue(InterpolatedValues('B1_DischargeStatus_FinalTime_Status_Rev',
                              LC_Chest_RetentionTime, LC_Chest_RetentionTime, '-1m'))
```

อ่านค่าสถานะในถัง ณ `t − (τ_LC + 5 นาที)` ถ้าเยื่ออยู่ในถังช่วง 08:00–10:41 จะไปถึง Press 1 ช่วง **08:29–11:10**

### Step 9: Notebook กำหนด Digester_ID

|                            |                                                                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **ไฟล์**         | `Lab_Analysis/realtime_pi_press1_analysis.ipynb` (cell 9)                                                                                 |
| **Tag ที่ใช้** | `PPPC_DP_Cooking.B1…B4_Discharge_FinalTime_Press1_Status` + `PULP-LINE2-KAPPA-PRESS1`, `…VISCOSITY-PRESS1`, `…BRIGHTNESS-PRESS1` |
| **Interval**         | Interpolated ทุก 1 ชม.                                                                                                                 |

```
Digester_ID = หม้อต้มใบแรก (B1→B4) ที่ Press1_Status > 0   ถ้าไม่มีสักใบ → 'D1'
```

## 3. จุดที่ควรตรวจหรือแก้

| # | Step | ปัญหา                                                                                                                                                                                    | ผลต่อการแบ่ง class                                                                  | ทางแก้ที่แนะนำ                                                                                                              |
| - | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| A | 3    | ใช้ Hour/Minute จึงข้ามชั่วโมงได้แค่ 1 ครั้ง (08:50 → 10:10 ได้ 20 แทน 80)                                                                                 | หน้าต่าง batch สั้นเกินจริง                                                 | `(B1_Wait_Timestamp - B1_Discharge_Timestamp)/60`                                                                                       |
| B | 2    | หา WAIT ตั้งแต่`'*-4h'` ไม่ได้เริ่มจาก T_D อาจได้ WAIT ที่เกิดก่อน DISCHARGE                                                                        | Step 3 ติดลบหรือผิด                                                                 | `FindEq('B1_Current_Sequence', B1_Discharge_Timestamp, '*', "WAIT")`                                                                    |
| C | 6    | เมื่อใบที่ถือสถานะหมดช่วงแล้วมีใบอื่นรอมากกว่า 1 ใบ ใบที่รอทุกใบจะได้สถานะพร้อมกัน 1 รอบ                     | 1 รอบการคำนวณได้ 2 ใบพร้อมกัน notebook เลือกเลขน้อยกว่า | ตัดสินจาก "ไม่มีใบไหนอยู่ในช่วงที่เก่ากว่า" โดยใช้ Timestamp แทนสถานะรอบก่อน |
| D | 1    | หน้าต่าง 4 ชม.: ถ้า T_D เก่ากว่า 4 ชม.แต่ยังไม่ถึง T_F (flow ต่ำ)                                                                                       | batch ถูกตัดกลางทาง                                                                | ขยายหน้าต่าง หรือเก็บ T_D เป็น attribute                                                                          |
| E | 6    | อ่านสถานะรอบก่อน จึงเป็น state machine ถ้า backfill หรือ recalc ผลอาจต่างจากตอนคำนวณสด                                                    | ข้อมูลย้อนหลังแบ่ง class ไม่ตรงกับข้อมูลเดิม               | ระวังตอน backfill และตรวจ Scheduling                                                                                       |
| F | 6, 8 | ชื่อ output ของ B1 (`_Rev`) ไม่เหมือน B2–B4 และ `B1_Discharge_FinalTime_Status` ตัวเก่ายังอยู่                                                          | ถ้า Press 3 อ่านผิดตัว B1 จะหาย                                               | ตั้งชื่อให้เป็นแบบเดียวกัน                                                                                      |
| G | 8    | `InterpolatedValues` ทำให้ค่าสถานะเป็นทศนิยม (พบ 0.5, 0.25, 3.2187 ในข้อมูล)                                                                               | ช่วงรอยต่อแบ่ง class ไม่ชัด                                                 | `PrevVal('B1_DischargeStatus_FinalTime_Status_Rev', LC_Chest_RetentionTime)`                                                            |
| H | 4, 7 | Step 4: flow = 0 จะหารด้วยศูนย์ · Step 7: flow ≤ 0 ได้ τ_LC = 0 (lag เหลือ 5 นาทีทั้งที่เยื่อค้างอยู่) · flow ต่ำได้ lag ยาวมาก | batch ช่วงผลิตช้าหรือหยุด (กลุ่ม Abnormal) แบ่ง class ผิด        | จำกัดค่า เช่น > 180 นาที →`NoOutput()`                                                                                 |
| I | 9    | ชั่วโมงที่ไม่มีหม้อต้มไหน active ถูกนับเป็น D1                                                                                                             | N ของ D1 สูงเกินจริง                                                              | fallback เป็น`None` แล้วตัดแถวทิ้ง                                                                                    |

## 4. เรื่องที่ยังค้าง

- [ ] ชื่อตัวแปร `LCChest_RetentionTime` (Step 7) กับ `LC_Chest_RetentionTime` (ใน expression ของ Step 8) ตรงกันหรือไม่
- [ ] Analysis Press1 ของ B2–B4 อ่านจาก `Bn_Discharge_FinalTime_Status` หรือไม่
- [ ] AF attribute `B1_DischargeStatus_FinalTime_Press1_Status` ผูกกับ PI Point ชื่ออะไร (notebook ใช้ `PPPC_DP_Cooking.B1_Discharge_FinalTime_Press1_Status`)
- [ ] Scheduling ของแต่ละ Analysis (Periodic กี่นาที หรือ Event-triggered)

---

## 5. ขั้นต่อไป: After Press 3

### เส้นทางเยื่อ (จาก flow diagram)

```
Batch #1–#4 → Discharged Tank (800 m3) → Screening → BSW → [Chest ก่อน Press 1 (? m3)] → Press 1
  → NaOH + O2 → O2 Tank 1 (95 m3) → O2 Tank 2 (145 m3) → LC Chest 1 (110 m3) → Press 2
  → LC Chest 2 (125 m3) → Press 3 → Unbleached HD Tower
```

| ถัง                                | ปริมาตร                     | อยู่ระหว่าง  | ใช้ในสูตรตอนนี้       |
| ------------------------------------- | ---------------------------------- | ----------------------- | ------------------------------------ |
| Discharged Tank                       | 800 m3                             | Digester → Screening   | Step 4 (`Time_Duration_Batch`) ✓  |
| Chest ก่อน Press 1 (หลัง BSW) | **ไม่มีในตาราง** | BSW → Press 1          | Step 7 ใช้**125 m3** ❓     |
| O2 Tank 1                             | 95 m3                              | Press 1 → O2 Tank 2    | –                                   |
| O2 Tank 2                             | 145 m3                             | O2 Tank 1 → LC Chest 1 | –                                   |
| LC Chest 1                            | 110 m3                             | ODL → Press 2          | –                                   |
| LC Chest 2                            | 125 m3                             | Press 2 → Press 3      | `11. LC Chest 2 Retention Time` ✓ |

> ⚠️ **ต้องตรวจ Step 7:** `LC Chest Retention Time` (lag ไป Press 1) ใช้ **125 m3** กับ `4. LC Chest Outlet Flow` แต่ใน diagram ถังก่อน Press 1 คือถังหลัง BSW ซึ่งไม่อยู่ในตารางปริมาตร ส่วน 125 m3 เป็นขนาดของ **LC Chest 2 (ก่อน Press 3)** เป็นไปได้ว่าค่า 125 ถูกคัดลอกมา ต้องยืนยันขนาดของถังก่อน Press 1 และเวลาผ่าน Screening กับ BSW (ตอนนี้ครอบคลุมด้วย offset 5 นาทีหรือไม่)

### LC Chest 2 (ตรวจแล้ว)

```
11. LC Chest 2 Retention Time = 125 / '11. LC Chest#2 Flow' × 60
'11. LC Chest#2 Flow' = '11. Press 3 Feed Flow#1' + '11. Press 3 Feed Flow#2'
ตรวจกับค่าบนหน้าจอ: 125 / 311.53 × 60 = 24.07 ✓ (หน้าจอแสดง 24.074)
```

### Lag จาก Press 1 ถึง Press 3 (steady state)

```
τ_P1→P3 = τ_O2T1 + τ_O2T2 + τ_LC1 + τ_LC2 (+ offset ท่อ/Press 2)

τ_O2T1 = 95  / Q_ODL × 60
τ_O2T2 = 145 / Q_ODL × 60
τ_LC1  = 110 / ('9. Press 2 Feed Flow#1' + '9. Press 2 Feed Flow#2') × 60
τ_LC2  = 125 / ('11. Press 3 Feed Flow#1' + '11. Press 3 Feed Flow#2') × 60   (มีอยู่แล้ว)
```

ตัวอย่างจากค่าบนหน้าจอ:

- τ_LC1 = 110 / (163.24 + 161.94) × 60 ≈ **20 นาที**
- τ_LC2 ≈ **24 นาที**
- τ_O2T1 + τ_O2T2 = 240 / Q_ODL × 60 เช่น ถ้า Q_ODL ≈ 100 m3/h จะได้ **≈ 144 นาที**

ช่วง O2 Tank 1 + 2 (240 m3) เป็นช่วงที่ lag มากที่สุด ค่า Q_ODL จึงสำคัญที่สุด

**Q_ODL (flow ผ่าน O2 reactor) มี 2 ทางเลือก:**

1. ใช้ tag flow ของ MC pump ที่ป้อน ODL ถ้ามี ← ต้องหาชื่อ tag
2. คำนวณจาก Production และ consistency: `Q ≈ Prod_ODL (ADT/d) × 0.9 / (Cons%/100) / 24` (m3/h, ประมาณความหนาแน่นเป็น 1)

### โครง Analysis ที่เสนอ

ต่อจากสถานะที่ Press 1 เลย ไม่ต้องคำนวณใหม่ตั้งแต่ถังระบาย:

```
Press3_Time = '*' - ((τ_O2T1 + τ_O2T2 + τ_LC1 + τ_LC2 + offset) * 60)
B1_…_Press3_Status = PrevVal('B1_DischargeStatus_FinalTime_Press1_Status', Press3_Time)
```

ต้องยืนยันกับทีม process ก่อนเขียน Analysis:

- [ ] ขนาดของถังก่อน Press 1 (หลัง BSW) และการใช้ 125 m3 ใน Step 7 ถูกต้องหรือไม่
- [ ] tag flow ผ่าน O2 reactor (Q_ODL) หรือ tag consistency ของ ODL feed
- [ ] offset ของท่อ, Press 2 และ Press 3 (ใช้ 5 นาทีแบบเดียวกันหรือไม่)
- [ ] ควรแก้ปัญหา A, B, G, H ก่อน เพื่อไม่ให้ความคลาดเคลื่อนสะสมต่อไปถึง Press 3
