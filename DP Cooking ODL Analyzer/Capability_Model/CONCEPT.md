# แนวคิด: ทำนายคุณภาพ batch จาก "กล่อง" ในอดีต (predict.py)

สั้น ๆ: **ไม่ใช่การเทรนโมเดล** แต่เป็นการ **เปิดตาราง** (lookup)

## หลักการ

1. `capability.search()` สร้างตาราง `res` = รายการ "กล่อง" (box)
   แต่ละกล่อง = เงื่อนไขช่วงของ X เช่น *Prehyd 63–75 นาที + P-temp 164–166°C*
   พร้อมค่าเฉลี่ย Viscosity / Kappa และ Cp ของ batch ที่เคยตกในกล่องนั้น
2. `predict.score(res, x)` เอา X ของ batch หนึ่ง (ที่ **จบ process แล้ว**)
   ไปเทียบว่าตกกล่องไหนบ้าง → คืนตารางกล่องที่เข้า เรียงตาม cp ดีสุด
3. `predict.consensus()` รวมทุกกล่องเป็นคำทำนายเดียว (ถ่วงน้ำหนักด้วย N)

ไม่มีไฟล์โมเดลต้องเซฟ — "โมเดล" คือ `res` ซึ่งสร้างใหม่จาก golden ได้ทุกเมื่อ

## จังหวะทำนาย (สำคัญ)

ทำนาย **ตอน batch จบ discharge** — ตอนนั้น X ครบทุกตัวแล้ว
(`pfactor_overshoot` วิ่งต่อจนจบ Hot Liquor Filling, ไม่ใช่จบ prehyd)
แต่ Y จากแลปยังไม่ออก (ต้องรออีกหลายชั่วโมง) → ยังเป็นการทาย **ล่วงหน้า**

```
batch จบ discharge → X ครบ → score(X) ทำนาย Y/cp → รอแลปออก → เช็คว่าตรงไหม
```

## ผลทดสอบ (backtest, leave-one-out, 2026-11-05)

| ตัววัด | lookup | baseline (เดาค่าเฉลี่ย) | ผล |
|---|---|---|---|
| Viscosity MAE | 27.7 | 33.0 | ดีกว่า ~16% |
| Kappa MAE | 0.68 | 0.71 | ดีกว่าเล็กน้อย |
| ทาย in/out-of-spec ตรง | 76% | — | 3 ใน 4 |
| ครอบคลุม | 100% | — | ทุก batch ตก ≥1 กล่อง |

สรุป: **ดีกว่าเดาค่าเฉลี่ยจริง** แต่ยังไม่แม่นระดับคุมกระบวนการ (Cp ยังต่ำ ~0.3–0.7)
ใช้เป็น "สัญญาณเตือนล่วงหน้า" ได้ ไม่ใช่ตัวตัดสิน

## วิธีใช้

```python
import predict
x = {"pfactor_overshoot":40, "prehydrolysis_minutes":70, "digester":3,
     "pfactor_temp_setpoint_last_prehydrolysis":165, ...}   # ค่า X ของ batch
scored, cons = predict.predict(x)     # สร้าง res + score ในคำสั่งเดียว
# scored = ตารางกล่องที่เข้า, cons = คำทำนายรวม
```

X ป้อนได้ 2 แบบ: คีย์เป็นชื่อคอลัมน์ (`pfactor_overshoot`) หรือชื่อสั้น (`P-temp SP`)

## ค่า X มาจากไหน

- **ทดสอบ (ตอนนี้):** พิมพ์เอง หรือ `realtime_pi/fetch_current.from_csv(path)`
- **realtime (ทีหลัง):** `realtime_pi/` ดึงจาก PI — ดู `realtime_pi/config.py`
  (endpoint, payload, tag map). **agent ไม่แตะ PI** — คุณรันเอง

## ไฟล์เกี่ยวข้อง

| ไฟล์ | หน้าที่ |
|---|---|
| `predict.py` | `score()` + `consensus()` + `predict()` + `backtest()` |
| `realtime_pi/config.py` | ตั้งค่า PI (endpoint / payload / tag) — อ่าน/แก้ได้ |
| `realtime_pi/fetch_current.py` | โครงดึง X จาก PI + `from_csv()` + demo |
| `capability.py` | `search()` สร้างกล่อง (ของเดิม) |
