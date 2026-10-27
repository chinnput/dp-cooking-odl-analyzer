**เจอconceptใหม่ๆ**

	ถ้าในช่วงที่คุณภาพไม้เริ่มตก ให้ปรับค่า อะไรสักอย่างเพื่อดันViscosityขึน

## **Phase 0 แลปข้อมูล SharePoint เข้า PI**

## **Phase 1 Core Objective & Baseline KPI**

	-หาBaseline Digester ที่ดีที่สุดเพื่อไปเป็นRef
	-หาAbnormal เทียบของตัวเองและตัวอื่น

	อุณหภูมิต้องถูก cooldown แล้วค่อยdischarge

	Setpont ทั้ง 4 Digester เท่ากัน
	Focusที่ LP, MP, WL. Liquor, BL. Liquor
	WL. Liquor, BL. Liquor มีโอกาสที่ alkalineไม่เท่ากัน ต้องไปโฟกัส ที่ alkaline
	setpoint แต่ละ Pressure แตกต่างกัน
	ที่น้ำหนักแต่ละใบไม่เท่ากัน ต้องไปดูว่าส่งผลต่อQualityมั้ย ถ้าไม่อาจเป็นเพราะตัวsensor gramma 	source ตรวจเร็วเกิน อาจเพี้ยน
	เพราะถังsizeเท่ากัน
	มีปัญหาวาล์วชอบเปิดไม่สุด ถ้าสามารถตรวจจับได้ จะช่วยได้เยอะ
	P-Factor อาจเทียบกับ Lap quality ได้
	Focus ที่ PHP, กลุ่มการใช้Steam
	Focus Viscos 1.การปรับไม่เหมาะสม 2. คุณภาพไม้
	ถ้าไม้เก่า Viscos จะต่ำ ถ้าปกติ Kappa and Viscos จะขึ้นลงล้อตามกัน
	ไม่ค่อย concern Brightness
	ถ้าอัดนานsteamนานเกิน มันจะยุ่ย viscos จะ drop

## **Phase 2: การจัดเตรียม ทำความสะอาด และเทียบเวลาข้อมูล (Data Ingestion, Cleaning & Time-Shift Alignment)**

	Step1: Data tag & ค้ด ที่ผิดปกติ

P-factor (prehydrolysis)

| Tag                   | PI_Description                 |
| --------------------- | ------------------------------ |
| PM2.104D1PFACTOR.CALC | DIGESTOR1 P-FACTOR             |
| PM2.104D1PFTEMP.CALC  | DIGESTOR1 P-FACT TEMP          |
| PM2.104D2OPESPPF.CALC | DIGESTOR2 P-FACTOR SETPOINT    |
| PM2.104D2OPESPPT.CALC | DIGESTOR2 P-FACT TEMP SETPOINT |
| PM2.104D2PFACTOR.CALC | DIGESTOR2 P-FACTOR             |
| PM2.104D2PFTEMP.CALC  | DIGESTOR2 P-FACT TEMP          |
| PM2.104D3OPESPPF.CALC | DIGESTOR3 P-FACTOR SETPOINT    |
| PM2.104D3OPESPPT.CALC | DIGESTOR3 P-FACT TEMP SETPOINT |
| PM2.104D3PFACTOR.CALC | DIGESTOR3 P-FACTOR             |
| PM2.104D3PFTEMP.CALC  | DIGESTOR3 P-FACT TEMP          |
| PM2.404D4OPESPPF.CALC | DIGESTOR4 P-FACTOR SETPOINT    |
| PM2.404D4OPESPPT.CALC | DIGESTOR4 P-FACT TEMP SETPOINT |
| PM2.404D4PFACTOR.CALC | DIGESTOR4 P-FACTOR             |
| PM2.404D4PFTEMP.CALC  | DIGESTOR4 P-FACT TEMP          |

Alkali & Liquor Strength

| Tag              | PI_Description       | Unit   |
| ---------------- | -------------------- | ------ |
| PM2.404AIC667:MV | ALK. ACC2            | g/l EA |
| PM2.404AIC670:MV | ALKALI ACCUMULATOR 1 | g/l    |
| PM2.404AI446     | DIG.4 Alkali         | g/l    |

Conductivity (BL/HBL) (การนำไฟฟ้า)

| Tag              | PI_Description | Unit  |
| ---------------- | -------------- | ----- |
| PM2.104AIC664:MV | B.L.COND       | MS    |
| PM2.104CIC551:MV | B.L COND       | mS/cm |
| PM2.104CIC660:MV | HBL ACC COND   | mS/cm |

Steam Supply Transmitters

| Tag               | PI_Discription       | Unit   |
| ----------------- | -------------------- | ------ |
| PM2.104FI137      | DIG.1 STEAM TO HEAT. | ton/h  |
| PM2.104PIC102:MV  | DIG.1 LP-STEAM       | bar    |
| PM2.104TIC120:MV  | DIG.1 STEAM HEATER   | C      |
| PM2.404HIC144:MV  | DIG.1 LP STEAM       | %      |
| PM2.404HIC145:MV  | DIG.1 MP STEAM       | %      |
| PM2.104FI237      | DIG.2 STEAM TO HEAT. | ton/h  |
| PM2.104PIC202:MV  | DIG.2 LP-STEAM       | bar    |
| PM2.104TIC220:MV  | DIG.2 STEAM HEATER   | C      |
| PM2.404HIC244:MV  | DIG.2 LP STEAM       | %      |
| PM2.404HIC245:MV  | DIG.2 MP STEAM       | %      |
| PM2.104FI337      | DIG.3 STEAM TO HEAT. | ton/h  |
| PM2.104PIC302:MV  | DIG.3 LP-STEAM       | bar    |
| PM2.104TIC320:MV  | DIG.3 STEAM HEATER   | C      |
| PM2.404HIC344:MV  | DIG.3 LP STEAM       | %      |
| PM2.404HIC345:MV  | DIG.3 MP STEAM       | %      |
| PM2.404HIC444:MV  | DIG.4 LP Steam       | %      |
| PM2.404HIC445:MV  | DIG.4 MP Steam       | %      |
| PM2.404PIC402:MV  | DIG.4 LP-Steam       | Bar    |
| PM2.404TIC420:MV  | DIG.4 Steam Heater   | C      |
| PM2.104CIS612     | HEAT EXCH.WL/STEAM   | miS/cm |
| PM2.104CIS644     | HEAT EXCH.WL/STEAM   | miS/cm |
| PM2.104FI508_CALC | MP Steam (Cooking)   | ton/h  |
| PM2.104FIC508:MV  | MP STEAM             | ton/h  |
| PM2.104FIQ507     | LP STEAM             | ton/h  |
| PM2.104FIQ508     | MP STEAM             | ton/h  |
| PM2.104LIC613V:MV | WL/STEAM CLEAN COND  | %      |
| PM2.104LIC613W:MV | WL/STEAM DIRTY COND  | %      |
| PM2.104LIC645V:MV | BL/STEAM CLEAN COND  | %      |
| PM2.104LIC645W:MV | BL/STEAM DIRTY COND  | %      |
| PM2.104PI534      | MP STEAM             | bar    |
| PM2.104PI535      | LP STEAM             | bar    |
| PM2.104TI537      | INLET MP STEAM TEMP  | C      |
| PM2.104TI538      | LP STEAM             | C      |
| PM2.104TI647      | HEAT EXCH WL/STEAM   | C      |
| PM2.104TIC614:MV  | HEAT EXCH.WL/STEAM   | C      |
| PM2.104TIC642:MV  | HEAT EXCH.BL/STEAM   | C      |
| PM2.104TIC642A:MV | STEAM C/V_NEW H.EXCH | 'C     |
| PM2.404FI437      | Steam H. 404.044     | Ton/h  |
| PM2.404FI724      | LP STEAM FLOW        | TON/H  |
| PM2.404FI725      | MP STEAM FLOW        | TON/H  |
| PM2.404HIC006:MV  | MP STEAM             | %      |
| PM2.404PI718      | Flash steam for Hex  | bar    |
| PM2.404PI723      | Flash steam to HEX   | mBar   |
| PM2.404PIC804:MV  | HEAT EXCH.WL/STEAM   | BAR    |
| PM2.405FI004      | Steam Flow           | T/H    |
| PM2.405PI003      | Steam Pressure       | Bar    |

CIRCULATION Temp

| Tag          | PI_Discription     | Unit |                               |
| ------------ | ------------------ | ---- | ----------------------------- |
| PM2.104TI123 | DIG.1 CIRCULATION  | C    |                               |
| PM2.104TI223 | DIG.2 CIRCULATION  | C    |                               |
| PM2.104TI323 | DIG.3 CIRCULATION  | C    |                               |
| PM2.404TI423 | DIG.4 Bottom Circ. | C    | เดาว่าDiscriptionผิด |

Bottom Temperatures

| Tag          | PI_Discription     | col3 |
| ------------ | ------------------ | ---- |
| PM2.104TI118 | DIG.1 BOTTOM CIRC. | C    |
| PM2.104TI218 | DIG.2 BOTTOM CIRC. | C    |
| PM2.104TI318 | DIG.3 BOTTOM CIRC. | C    |
| PM2.404TI418 | DIG.4 Bottom Circ. | C    |

Displacement & Blow Line Temps

| Tag           | PI_Discription      | Unit |
| ------------- | ------------------- | ---- |
| PM2.104TIS114 | DIG.1 DISPL. LIQUOR | C    |
| PM2.104TIS214 | DIG.2 DISPL. LIQUOR | C    |
| PM2.104TIS314 | DIG.3 DISPL. LIQUOR | C    |
| PM2.404TIS414 | DIG.4 Displ. Liq.   | C    |

Digester Pressures

| Tag              | PI_Discription | Unit |
| ---------------- | -------------- | ---- |
| PM2.104PIC104:MV | DIG.1 PRESSURE | BAR  |
| PM2.104PIC204:MV | DIG.2 PRESSURE | BAR  |
| PM2.104PIC304:MV | DIG.3 PRESSURE | BAR  |
| PM2.404PIC404:MV | DIG.4 PRESSURE | BAR  |

Ventilation / Air Evacuation Temperature

	เซนเซอร์วัดอุณหภูมิบริเวณท่อระบายอากาศ/ไล่ก๊าซ

	ดูคร่าวๆ ค่าmin max ไม่เท่ากันในแต่ละ digester

| Tag          | PI_Discription       | Unit |            |
| ------------ | -------------------- | ---- | ---------- |
| PM2.104TI125 | DIG.1 VENTILATION    | C    |            |
| PM2.104TI225 | DIG.2 VENTILATION    | C    |            |
| PM2.104TI325 | DIG.3 VENTILATION    | C    |            |
| PM2.404TI425 | DIG.4 Air Evaquation | C    | ค้าง90 |

วัดอุณหภูมิน้ำยาต้ม ระหว่างน้ำยาขาว (White Liquor) และน้ำยาดำ (Black Liquor)

	หากใช้อุณหภูมิห้องหรืออุณหภูมิต่ำ สารเคมีด่างจะไม่สามารถย่อยสลายและตัดพันธะเคมีในโครงสร้างลิกนินเพื่อแยกเส้นใยออกจาก	กันได้อย่างมีประสิทธิภาพ

| Tag           | PI_Discription       | Unit |                                                            |
| ------------- | -------------------- | ---- | ---------------------------------------------------------- |
| PM2.104TI611A | HEAT EXCH IN         | C    | อุณหภูมิด้านขาเข้าของน้ำยาต้ม |
| PM2.104TI611  | HEAT EXCHANGER WL/BL | C    |                                                            |

pumpเริ่มทำงานตอน HEAT&COOK

| Tag         | PI_Discription  | Unit |
| ----------- | --------------- | ---- |
| PM2.104M561 | DIG 1 CIRC.PUMP | A    |
| PM2.104M562 | DIG 2 CIRC.PUMP | A    |
| PM2.104M563 | DIG 3 CIRC.PUMP | A    |
| PM2.404M564 | DIG 4 CIRC.PUMP | A    |

Press 1 Lab Quality

| Tag                          | PI_Discription    | Unit |
| ---------------------------- | ----------------- | ---- |
| PULP-LINE2-KAPPA-PRESS1      | press1_kappa      |      |
| PULP-LINE2-VISCOSITY-PRESS1  | press1_viscosity  |      |
| PULP-LINE2-BRIGHTNESS-PRESS1 | press1_brightness |      |

Digester Chip Weight

| Tag           | PI_Discription       | Unit |                  |
| ------------- | -------------------- | ---- | ---------------- |
| PM2.104WI129  | DIG.1 WEIGHT         | ton  |                  |
| PM2.104WI229  | DIG.2 WEIGHT         | ton  |                  |
| PM2.104WI329  | DIG.3 WEIGHT         | ton  |                  |
| PM2.404WI429  | DIG.4 Weight         | Ton  |                  |
| PM2.102LIA104 | CHIPS BIN LEVEL      | %    |                  |
| PM2.102LIA142 | CHIP SILO Comp 8-11  | %    |                  |
| PM2.102LIA143 | Chip Silo Comp 8-11  | %    |                  |
| PM2.102LIA147 | Chip Silo Pl2 Comp 2 | %    |                  |
| PM2.102LIA148 | Chip Silo Pl2 Comp 3 | %    |                  |
| PM2.102LIA149 | Chip Silo Pl2 Comp 4 | %    |                  |
| PM2.102WI106  | 0                    | ton  |                  |
| PM2.404MI801  | CHIP MOISETURE       | %    | ค่าค้าง35 |

	Step2: ตรวจสอบเฟสสกัดคาร์โบไฮเดรต (Pre-hydrolysis Phase)

	ค่าสะสม P-factor Actual (  PFACTOR.CALC ) เทียบกับ  Setpoint (  OPESPPF.CALC ) และระยะเวลา `PHP_T`

	Step3: **ตรวจสอบเฟสต้มกำจัดลิกนิน (Heat & Cook Phase)**

		- อุณหภูมิน้ำหมุนเวียนหลัก (`TI123`–`TI423`), อัตราการจ่ายไอน้ำ และการสะสมค่า H-factor

		- ตรวจสอบว่าเกิดการต้มลากเวลานานเกินไป ( Over-cooking ) หรืออุณหภูมิสูงเกินไปหรือไม่ เพื่อป้องกันค่า Viscosity ดิ่งลง

	Step4: **ตรวจสอบเฟสตัดจบปฏิกิริยา (Displacement Phase)**

		อุณหภูมิน้ำล้าง (`TIS114`–`TIS414`) และประสิทธิภาพการเปลี่ยนถ่ายน้ำต้ม (Displacement Efficiency)

## **Phase 3: Analytic**

### 3.1 Lag Time Alignment

* [X] **Lag time** — เมื่อ Digester after Press 1 เลื่อนเวลาแล้ว ตัว sensor parameter ควรถูกเลื่อนตามผล After Press 1
  1. รู้ก่อนว่า tag อะไรบ้างที่จะใช้ อยู่ตรงไหน
  2. lag time เวลาเท่าไหร่ สำหรับวิเคราะห์ที่ After Press 1

### 3.2 Golden Batch Reference

* [X] **หา Best Baseline Quality (Golden Batch Reference)** — รวบรวมข้อมูล Batch ที่ได้ค่า Viscosity และ Kappa Number อยู่ในเกณฑ์มาตรฐานสูงสุด เพื่อกำหนดเป็น Baseline Profile Reference
  สมมติว่าถ้าได้แล้ว เช่น
  KAPPA = 9.0-9.5
  VISCOSITY = 725-775
  ทุกDigester ใช้เท่ากันก่อน
* [ ] **หา Parameter ในแต่ละ Batch ที่ได้Good มาแล้ว**
  หาว่าparameterแต่ละDigesterมีค่าเฉลี่ยเท่าไหร่
  parameter ที่เกี่ยวข้องกับ Viscosity Focusที่ hydrolysis
  1.P-factor ส่งผลให้hydrolysis time ช้าเร็ว ต้องไปดูต่อว่าการที่P-factorเท่า แต่ Temp ไม่เท่าก้ได้ แค่เวลาเปลี่ยนตาม ต้องดูว่าที่ tempไหน ดีที่สุด P-factor อาจมาจาก Steam Heater
  จากที่ทดลอง steam temp ไม่ค่อยเปลี่ยน P-Factor setpoint เปลี่ยน
  2.Chip weight
  3.Chip moisture
  4.steam_heater_flow ถ้าสูงเกิน P-Factor สะสมเร็วขึ้น  อาจทำให้ cellulose ถูกทำลาย

### 3.3 Digester Comparison

* ** การวิเคราะห์เปรียบเทียบ (Self & Cross-Digester Comparison)**

  * เปรียบเทียบกับตัวเอง (Self-Comparison): ตรวจสอบความผันผวนระหว่างรอบการต้มของหม้อเดียวกัน
  * 
  * เปรียบเทียบระหว่างหม้อต้ม (D1 vs D2 vs D3 vs D4): เนื่องจาก Setpoint หลักของทั้ง 4 หม้อต้มถูกตั้งไว้เท่ากัน ให้ทำการเปรียบเทียบเพื่อหา Root Cause ว่าหม้อใดมีพฤติกรรมเบี่ยงเบนไปจากกลุ่ม

### 3.4 Root-Cause Checks

* [ ] **Cold Blow Concept** — ตรวจสอบอุณหภูมิในเฟส DISPLACEMENT ว่าถูกกดอุณหภูมิลงอย่างสมบูรณ์ก่อนทำการ Discharge หรือไม่ เพื่อหยุดปฏิกิริยาการต้มและป้องกันเส้นใยถูกย่อยสลายทางกล
* [ ] **ค่าด่างจากถังสะสม** — ตรวจสอบค่าด่างจากถังสะสม
* [ ] **การตรวจจับปัญหาวาล์วเปิดไม่สุด (Valve Anomaly Detection Logic)**
  * (PM2.104FIC532:MV) flow ไม่ค่อยมีปัญหา นิ่งตลอด เปิดลากยาว
* [ ] **วิเคราะห์ P-Factor เทียบกับผลแล็บ**
* [ ] **Over-cooking** — ถ้าอัดไอน้ำนานเกินไป เนื้อไม้ยุ่ย Viscos ดิ่ง
  * จากการเช็ค (PM2.404HIC145:MV) DIG.1 MP STEAM เปิดวาล์วจนกว่าอุณหภูมิของ (PM2.104TIC120:MV) STEAM HEATER ไปถึงที่ 164 องศา จึงปิดวาล์ว แล้วอุณหภูมิก็ดันตัวเองไปเรื่อยๆ จนถึงจุดนึงดรอปลง แล้วก็ขึ้นไปอีกเพื่อดัน P-factor แต่จากสังเกต วาล์วก็ไม่ได้เปิดทั้ง LP และ MP
  * ตั้งคำถาม: แล้วอะไรดันอุณหภูมิขึ้นไป
  * P-Factor คือ "ตัวเงื่อนไขการเปลี่ยนเฟส" (Phase Transition Condition) ไม่ใช่ตัวปรับตำแหน่งวาล์วโดยตรง
* [ ] **ไม้เก่า**
  * ไม้เก่า
  * อัด steam นานเกิน
