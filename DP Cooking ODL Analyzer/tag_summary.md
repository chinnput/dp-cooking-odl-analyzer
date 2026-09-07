# สรุปรายละเอียด Tags และ พารามิเตอร์ทั้งหมดในโปรเจกต์ (Tag Summary Reference)

เอกสารฉบับนี้รวบรวมและอธิบายรายชื่อ **PI Tags** (ผลแล็บ QA) และ **Process Parameters** (เซนเซอร์การผลิต DCS) ทั้งหมดที่ใช้งานในโปรเจกต์ **DP Cooking ODL Analyzer (Pulp Line 2)**

---

## หมวดที่ 1: QA Lab Quality Tags (19 PI Tags จาก OneDrive Logbook)

เป็นค่าผลแล็บวัดคุณภาพเยื่อกระดาษรายชั่วโมงที่ดึงมาจาก Excel Log Book บน OneDrive/SharePoint และส่งเข้า **AVEVA PI Server (`VPKGDRBPPI01`)** ผ่านสคริปต์ `onedrive_to_pi`

| #                                                                                                      | ชื่อตัวแปร (Field Name) | ชื่อ PI Tag บน PI Server   | คอลัมน์ Excel | จุดวัด (Stage) | ความหมายและหน่วย                                                    |
| ------------------------------------------------------------------------------------------------------ | --------------------------------- | -------------------------------- | -------------------- | -------------------- | ----------------------------------------------------------------------------------- |
| **[Kappa Number - ดัชนีปริมาณลิกนินที่เหลือในเยื่อ]**            |                                   |                                  |                      |                      |                                                                                     |
| 1                                                                                                      | `Kappa_Press1`                  | `PULP-LINE2-KAPPA-PRESS1`      | Col F (Col 5)        | Press 1              | ค่า Kappa หลังผ่านการต้มออกจากหม้อต้มเข้า Press 1 |
| 2                                                                                                      | `Kappa_Press3`                  | `PULP-LINE2-KAPPA-PRESS3`      | Col G (Col 6)        | Press 3              | ค่า Kappa หลังผ่านการฟอกด้วยออกซิเจน (ODL)             |
| 3                                                                                                      | `Kappa_Eop`                     | `PULP-LINE2-KAPPA-EOP`         | Col H (Col 7)        | EOP Tower            | ค่า Kappa หลังผ่านทาวเวอร์ฟอก EOP                             |
| **[Viscosity - ค่าความหนืด / ความยาวแข็งแรงเส้นใย ($cm^3/g$)]** |                                   |                                  |                      |                      |                                                                                     |
| 4                                                                                                      | `Viscosity_Press1`              | `PULP-LINE2-VISCOSITY-PRESS1`  | Col I (Col 8)        | Press 1              | ความหนืดเยื่อที่ Press 1                                            |
| 5                                                                                                      | `Viscosity_Press3`              | `PULP-LINE2-VISCOSITY-PRESS3`  | Col J (Col 9)        | Press 3              | ความหนืดเยื่อที่ Press 3                                            |
| 6                                                                                                      | `Viscosity_D0`                  | `PULP-LINE2-VISCOSITY-D0`      | Col K (Col 10)       | D0 Tower             | ความหนืดเยื่อที่ทาวเวอร์ฟอก D0                           |
| 7                                                                                                      | `Viscosity_Eop`                 | `PULP-LINE2-VISCOSITY-EOP`     | Col L (Col 11)       | EOP Tower            | ความหนืดเยื่อที่ทาวเวอร์ฟอก EOP                          |
| 8                                                                                                      | `Viscosity_D1`                  | `PULP-LINE2-VISCOSITY-D1`      | Col M (Col 12)       | D1 Tower             | ความหนืดเยื่อที่ทาวเวอร์ฟอก D1                           |
| 9                                                                                                      | `Viscosity_D2`                  | `PULP-LINE2-VISCOSITY-D2`      | Col N (Col 13)       | D2 Tower             | ความหนืดเยื่อที่ทาวเวอร์ฟอก D2                           |
| **[Brightness - ค่าความสว่าง/ความขาวของเยื่อ (%)]**                   |                                   |                                  |                      |                      |                                                                                     |
| 10                                                                                                     | `Brightness_Press1`             | `PULP-LINE2-BRIGHTNESS-PRESS1` | Col P (Col 15)       | Press 1              | ความสว่างเยื่อที่ Press 1                                          |
| 11                                                                                                     | `Brightness_Press3`             | `PULP-LINE2-BRIGHTNESS-PRESS3` | Col Q (Col 16)       | Press 3              | ความสว่างเยื่อที่ Press 3                                          |
| 12                                                                                                     | `Brightness_D0`                 | `PULP-LINE2-BRIGHTNESS-D0`     | Col R (Col 17)       | D0 Tower             | ความสว่างเยื่อที่ทาวเวอร์ฟอก D0                         |
| 13                                                                                                     | `Brightness_Eop`                | `PULP-LINE2-BRIGHTNESS-EOP`    | Col S (Col 18)       | EOP Tower            | ความสว่างเยื่อที่ทาวเวอร์ฟอก EOP                        |
| 14                                                                                                     | `Brightness_D1`                 | `PULP-LINE2-BRIGHTNESS-D1`     | Col T (Col 19)       | D1 Tower             | ความสว่างเยื่อที่ทาวเวอร์ฟอก D1                         |
| 15                                                                                                     | `Brightness_D2`                 | `PULP-LINE2-BRIGHTNESS-D2`     | Col V (Col 21)       | D2 Tower             | ความสว่างเยื่อที่ทาวเวอร์ฟอก D2                         |
| **[pH - ค่าความเป็นกรด-ด่าง]**                                                 |                                   |                                  |                      |                      |                                                                                     |
| 16                                                                                                     | `pH_D0`                         | `PULP-LINE2-PH-D0`             | Col AA (Col 26)      | D0 Tower             | ค่า pH ที่ทาวเวอร์ D0                                                 |
| 17                                                                                                     | `pH_Eop`                        | `PULP-LINE2-PH-EOP`            | Col AB (Col 27)      | EOP Tower            | ค่า pH ที่ทาวเวอร์ EOP                                                |
| 18                                                                                                     | `pH_D1`                         | `PULP-LINE2-PH-D1`             | Col AC (Col 28)      | D1 Tower             | ค่า pH ที่ทาวเวอร์ D1                                                 |
| 19                                                                                                     | `pH_D2`                         | `PULP-LINE2-PH-D2`             | Col AD (Col 29)      | D2 Tower             | ค่า pH ที่ทาวเวอร์ D2                                                 |

---

## หมวดที่ 2: Process Sensor Parameters (31 พารามิเตอร์การผลิต DCS)

เป็นพารามิเตอร์ที่ดึงจากเซนเซอร์ DCS เรียลไทม์ นำมาประมวลผลคำนวณสถิติและจัดกลุ่ม Batch ใน `DP Cooking ODL Analyzer`

### 1. พารามิเตอร์กำลังการผลิตและการไหล (Production & Slurry Flow)

| ชื่อพารามิเตอร์ (Parameter Name) | หน่วย (Unit) | ความหมายและคำอธิบาย                                                                                    |
| ----------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `Production ODL (ADT/D)`                      | ADT/D             | อัตราการผลิตเยื่อในกระบวนการ ODL (Air-Dry Tons per Day)                                       |
| `Deknotting Feed Flow (m3/h)`                 | $m^3/h$         | อัตราการไหลของน้ำเยื่อที่ป้อนเข้าเครื่องคัดแยกปมไม้/ตาไม้         |
| `Deknotting Feed Cons (%)`                    | %                 | ค่าความเข้มข้นเนื้อเยื่อ (Consistency) ที่ป้อนเข้าเครื่องคัดแยกปมไม้ |
| `Screening Accept flow (m3/h)`                | $m^3/h$         | อัตราการไหลของน้ำเยื่อที่ดี ที่ผ่านการกรองตะแกรง Screening                 |
| `Press 1 Feed Cons (%)`                       | %                 | ค่าความเข้มข้นเนื้อเยื่อที่ป้อนเข้าเครื่องบีบล้างเยื่อ Press 1      |
| `Press 2 Feed Cons (%)`                       | %                 | ค่าความเข้มข้นเนื้อเยื่อที่ป้อนเข้าเครื่องบีบล้างเยื่อ Press 2      |
| `Press 3 Feed Cons (%)`                       | %                 | ค่าความเข้มข้นเนื้อเยื่อที่ป้อนเข้าเครื่องบีบล้างเยื่อ Press 3      |
| `Press 1 Dilute Screen (m3/h)`                | $m^3/h$         | อัตราการไหลของน้ำเจือจาง (Dilution Water) เติมเข้า Press 1                                |
| `Press 2 Dilute Screen (m3/h)`                | $m^3/h$         | อัตราการไหลของน้ำเจือจางเติมเข้า Press 2                                                  |
| `Press 3 Dilute Screen (m3/h)`                | $m^3/h$         | อัตราการไหลของน้ำเจือจางเติมเข้า Press 3                                                  |

### 2. พารามิเตอร์การจ่ายสารเคมีและไอน้ำ (Chemicals & Steam Feed)

| ชื่อพารามิเตอร์ (Parameter Name)       | หน่วย (Unit) | ความหมายและคำอธิบาย                                                                                   |
| ----------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `WHLiqu to DilSrew_White liquor (m3/h)`             | $m^3/h$         | อัตราการจ่ายน้ำยาขาว (White Liquor - NaOH+Na2S) เข้าสกรีวเจือจาง                     |
| `MP Steam Pulp Heat_Feed before Reactor 2 (t/h)`    | t/h               | อัตราการจ่ายไอน้ำความดันปานกลางเพื่ออุ่นเยื่อก่อนเข้า ODL Reactor 2 |
| `O2 to Mixer1_Oxygen feed at Reactor 1 (kg/h)`      | kg/h              | อัตราการจ่ายก๊าซออกซิเจนเข้า Mixer 1 ก่อนเข้า ODL Reactor 1                          |
| `O2 to pulp heater_Oxygen feed at Reactor 2 (kg/h)` | kg/h              | อัตราการจ่ายก๊าซออกซิเจนเข้า Pulp Heater ก่อนเข้า ODL Reactor 2                      |

### 3. พารามิเตอร์อุณหภูมิและความดัน (Temperature & Pressure Controls)

| ชื่อพารามิเตอร์ (Parameter Name)       | หน่วย (Unit) | ความหมายและคำอธิบาย                                                   |
| ----------------------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------- |
| `O2_Oxygen pressure (bar)`                          | bar               | ความดันของก๊าซออกซิเจนหลักที่จ่ายเข้าไลน์ ODL   |
| `O2-line_Temp Oxygen to ODL (oC)`                   | °C               | อุณหภูมิของก๊าซออกซิเจนหลักที่จ่ายเข้าไลน์ ODL |
| `O2 REACT PRESS.CTRL._Pressure at Reactor 1 (bar)`  | bar               | ค่าความดันควบคุมเป้าหมายที่ทาวเวอร์ ODL Reactor 1     |
| `O2 Reactor1_Pressure at Reactor 1 (bar)`           | bar               | ค่าความดันจริงที่วัดได้ในทาวเวอร์ ODL Reactor 1         |
| `O2 Reactor1 TOP_Pressure top Reactor 1_1 (bar)`    | bar               | ความดันยอดทาวเวอร์ ODL Reactor 1 (จุดวัดที่ 1)                |
| `O2 Reactor1 TOP_Pressure top Reactor 1_2 (bar)`    | bar               | ความดันยอดทาวเวอร์ ODL Reactor 1 (จุดวัดที่ 2)                |
| `Oxygen Reactor_Pressure top Reactor 1 (bar)`       | bar               | ความดันรวมบริเวณยอดทาวเวอร์ ODL Reactor 1                     |
| `O2 Reactor1 TOP_Temp top Reactor 1 (oC)`           | °C               | อุณหภูมิยอดทาวเวอร์ ODL Reactor 1                                     |
| `O2 Reactor1 Bottom_Temp bottom Reactor 1 (oC)`     | °C               | อุณหภูมิท้ายทาวเวอร์ (ด้านล่าง) ODL Reactor 1                |
| `O2 Reactor FeedTemp_Pulp temp feed Reactor 2 (oC)` | °C               | อุณหภูมิน้ำเยื่อก่อนป้อนเข้า ODL Reactor 2                   |
| `Oxygen Reactor_Temp top Reactor 2 (oC)`            | °C               | อุณหภูมิยอดทาวเวอร์ ODL Reactor 2                                     |

### 4. พารามิเตอร์ประสิทธิภาพจำเพาะ (Specific Consumption Parameters - คำนวณเพิ่ม)

| ชื่อพารามิเตอร์ (Parameter Name)  | หน่วย (Unit) | สูตรการคำนวณและคำอธิบาย                                                                                                                  |
| ------------------------------------------------ | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Specific Steam Consumption (t_ADT)`           | t/ADT             | $24.0 \times \text{Steam Flow (t/h)} / \text{Production (ADT/D)}$ ปริมาณไอน้ำที่ใช้ต่อการผลิตเยื่อ 1 ตัน                   |
| `Specific WHLiqu Consumption (m3_ADT)`         | $m^3/ADT$       | $24.0 \times \text{WHLiquor Flow (m3/h)} / \text{Production (ADT/D)}$ ปริมาณน้ำยาขาวที่ใช้ต่อการผลิตเยื่อ 1 ตัน         |
| `Specific O2 Mixer 1 Consumption (kg_ADT)`     | kg/ADT            | $24.0 \times \text{O2 Mixer 1 (kg/h)} / \text{Production (ADT/D)}$ ปริมาณออกซิเจนที่ Mixer 1 ต่อการผลิตเยื่อ 1 ตัน         |
| `Specific O2 Pulp Heater Consumption (kg_ADT)` | kg/ADT            | $24.0 \times \text{O2 Pulp Heater (kg/h)} / \text{Production (ADT/D)}$ ปริมาณออกซิเจนที่ Pulp Heater ต่อการผลิตเยื่อ 1 ตัน |

### 5. พารามิเตอร์สถานะและควบคุม Batch (Status Triggers)

| ชื่อพารามิเตอร์ (Parameter Name)                      | หน่วย (Unit) | คำอธิบาย                                                                                             |
| -------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------ |
| `Dig1_Discharge_BatchStatus` ถึง `Dig4_Discharge_BatchStatus` | Flag (0-4)        | สัญญาณบอกสภาวะการถ่ายเยื่อ (Discharge) จากหม้อต้ม D1–D4                 |
| `Dig1_Press1_BatchStatus` ถึง `Dig4_Press1_BatchStatus`       | Flag (0-4)        | สัญญาณบอกสภาวะเยื่อหม้อต้ม D1–D4 กำลังผ่านเครื่องล้าง Press 1 |

---

## หมวดที่ 3: โครงสร้างการผูกโยงข้อมูล (Tag Mapping Architecture)

```
[OneDrive Log Book (Excel)] ──> step1_fetch_onedrive.py ──> step2_time_matching.py ──> step3_pi_api_client.py
                                                                                               │
                                                                                       (Write via API)
                                                                                               ▼
[PI Vision Dashboard] <───────────────────────────────────────────────────────────── [AVEVA PI Server]
  │                                                                                            ▲
  └─────────── (Real-time Process Sensors: Flow, Production, Temp, Steam, Cons) ───────────────┘
```
