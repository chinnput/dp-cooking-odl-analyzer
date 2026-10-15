
**Phase 0 แลปข้อมูล SharePoint เข้า PI**

**Phase 1 Core Objective & Baseline KPI**

	:คุมคุณภาพเยื่อ (Quality-Driven)

	:คุมเสถียรภาพการผลิต (Process Stability)

**Phase 2: **จัดลำดับการวิเคราะห์ตามลำดับกระบวนการ** (Upstream to Downstream)**

	Step1: (Input & Preparation)

		Chip Weight (  WI  ), Chip Moisture (  MI801 ) และวิธีการ Chip Filling / Pre-steaming

	Step2: ตรวจสอบเฟสสกัดคาร์โบไฮเดรต (Pre-hydrolysis Phase)

ค่าสะสม P-factor Actual (  PFACTOR.CALC ) เทียบกับ  Setpoint (  OPESPPF.CALC ) และระยะเวลา `PHP_T`

	Step3: **ตรวจสอบเฟสต้มกำจัดลิกนิน (Heat & Cook Phase)**

		- อุณหภูมิน้ำหมุนเวียนหลัก (`TI123`–`TI423`), อัตราการจ่ายไอน้ำ และการสะสมค่า H-factor

		- ตรวจสอบว่าเกิดการต้มลากเวลานานเกินไป ( Over-cooking ) หรืออุณหภูมิสูงเกินไปหรือไม่ เพื่อป้องกันค่า Viscosity ดิ่งลง

	Step4: **ตรวจสอบเฟสตัดจบปฏิกิริยา (Displacement Phase)**

		อุณหภูมิน้ำล้าง (`TIS114`–`TIS414`) และประสิทธิภาพการเปลี่ยนถ่ายน้ำต้ม (Displacement Efficiency)

**Phase 3: ดูคุณภาพที่ Press 1 รายหม้อ**

	- Lag time 

		เมื่อDigester after press1 เลื่อนเวลาแล้ว ตัว sensor parameter ควรถูกเลื่อนตามผล After press1

		1.รู้ก่อน tagอะไรบ้างที่จะใช้ อยู่ตรงไหน
		2.lag time เวลาเท่าไหร่ สำหรับวิเคราะห์ที่ After press1

	- H-Factor

		คำนวณหาแค่จังหวะ Heat&Cook แล้วค่อยย้อนเวลามาดูจังหวะนั้นแล้วหยิบ H-Factor มาวิเคราะห์

**Phase 4: Connect Lab result & Digester Batch**

	

**Phase 3: การจัดการข้อมูลและการทำ Root Cause Analysis (Data-Driven Strategy)**

	1. คัดกรองเฉพาะ Tag สำคัญ (Key Performance Indicators) :

	2.เปรียบเทียบข้อมูลเป็นราย Batch (Batch-to-Batch Comparison) :

	3.ทำ Single-Variable Testing :
