# Pareto Front Analysis for Golden Batch Discovery

## สรุป

เพิ่มฟีเจอร์ **Pareto front analysis** เข้า `02_analysis.ipynb` เพื่อหาค่า Kappa และ Viscosity ที่เหมาะสมสำหรับ "golden batch" โดยไม่ต้องบอกค่า target ล่วงหน้า

---

## ไฟล์ที่เพิ่ม

### 1. `pareto_golden_batch.py`
Module ใหม่ที่มีฟังก์ชันหลัก:

```python
results = analyze_pareto(master, lab_linked, save_path="image/pareto_golden_batch.png")
```

**ผลลัพธ์ที่ได้:**
- `results['ideal_kappa']` — Kappa ที่เหมาะสมที่สุด
- `results['ideal_viscos']` — Viscosity ที่เหมาะสมที่สุด
- `results['golden_batches']` — DataFrame ของ batches ใกล้ ideal point
- Plot: Pareto front before/after 2-sigma filtering

---

## ขั้นตอน (Workflow)

### Step 1: ตรวจสอบเบื้องต้น
ก่อนรัน Pareto analysis ให้เช่ค:
- ข้อมูล lab_linked มี Kappa และ Viscosity ไหม
- Batch master มีก่อพอ (หลายร้อย batches)

### Step 2: รัน Pareto analysis
ใน `02_analysis.ipynb` cell ใหม่ (ท้ายของ notebook):

```python
from pareto_golden_batch import analyze_pareto

results = analyze_pareto(master, lab_linked, save_path='image/pareto_golden_batch.png')
```

**Output ที่จะเห็น:**
1. Plot: 2 subplots
   - Left: ข้อมูลทั้งหมด + Pareto front (แดง)
   - Right: หลัง 2-sigma filter + ideal point (ดาวทอง)

2. Print table:
   - Filtering summary (2-sigma)
   - Pareto front statistics
   - Ideal point value
   - Golden batch count & profile

### Step 3: ตีความผลลัพธ์

```
ideal_kappa = 7.92 (ค่าที่คาดว่าดี)
ideal_viscos = 705 (ค่าที่คาดว่าดี)
golden_batches: 45 batches
  D1: 12 batches, Kappa 7.90±0.15, Viscosity 704±8
  D2: 18 batches, Kappa 7.95±0.12, Viscosity 706±7
  ...
```

**สิ่งที่บอก:**
- Pareto ชี้ว่า Kappa ที่ดีสุด ≈ 7.92, Viscosity ≈ 705
- Golden batches (ใกล้ ideal) มี ~45 แถว
- D2 มีสุด (18 golden batches)

### Step 4: ใช้ ideal values เพื่อตั้งเกณฑ์ golden batch

ตอนนี้คุณมี **concrete target** ที่ derive จากข้อมูลจริง:

```python
kappa_target = results['ideal_kappa']  # 7.92
viscos_target = results['ideal_viscos']  # 705

# ตั้ง "golden zone" รอบๆ ideal
kappa_range = (kappa_target - 0.3, kappa_target + 0.3)  # ±0.3 tolerance
viscos_range = (viscos_target - 20, viscos_target + 20)  # ±20 tolerance

golden = master[
    (master['press1_kappa'] >= kappa_range[0]) & 
    (master['press1_kappa'] <= kappa_range[1]) &
    (master['press1_viscosity'] >= viscos_range[0]) & 
    (master['press1_viscosity'] <= viscos_range[1])
]

print(f"Golden batches (±tolerance): {len(golden)}")
print(golden.groupby('digester').size())
```

---

## อัลกอริทึม

### 1. Pareto Frontier
จุดที่อยู่บน Pareto front:
- ไม่มี point อื่นที่มี Kappa ≤ และ Viscosity ≥ พร้อมกัน

```
เส้นโค้ง Pareto: L-shaped
┌─────────────────────
│                  ★ (high K, high V)
│              ★★
│           ★★
│        ★
│  (low K)→ ★ (low V)
└─────────────────────
```

### 2. 2-Sigma Filter
ตัดออก outliers:
```
kept = (Kappa within mean ± 2σ) AND (Viscosity within mean ± 2σ)
```

### 3. Ideal Point (Closest to Utopia)
Utopia = (Kappa_min, Viscosity_max) — dream state ที่ไม่มีในโลกจริง

หา point บน Pareto ที่ใกล้ utopia สุด (ใช้ normalized Euclidean distance)

```
ideal = argmin( sqrt( norm_kappa² + (1 - norm_viscosity)² ) )
```

### 4. Golden Zone
Batches ที่อยู่ใน 5% normalized distance จาก ideal point

---

## ตัวแปรสำคัญ

| ตัวแปร | ค่า | หมายความ |
|------|-----|--------|
| `GOLDEN_THRESHOLD` | 0.05 | Golden zone = 5% ของ normalized space |
| `clean_mask` | boolean | True = ผ่าน 2-sigma filter |
| `pareto_idx_clean` | indices | Points บน Pareto front |

---

## ผลลัพธ์ที่ได้เป็น

### 1. Figure: `pareto_golden_batch.png`

![Description: Pareto front plot showing trade-off between Kappa and Viscosity]

- **Left:** All data + Pareto before filtering
- **Right:** Clean data + ideal point (gold star)
- **Legend:** 2-sigma bands, Pareto front, ideal point

### 2. Console Output

```
================================================================================
PARETO FRONT ANALYSIS RESULTS
================================================================================

Filtering by 2-sigma:
  Kappa: 8.04 ± 0.38 → [7.28, 8.80]
  Viscosity: 703 ± 22 → [659, 747]
  Removed: 45 outliers
  Kept: 859 batches

Pareto front (clean data):
  Points on front: 32
  Kappa range: 7.28 – 8.78
  Viscosity range: 658 – 747

Ideal point (closest to utopia):
  Kappa: 7.92
  Viscosity: 705
  Digester: D2

Golden batches (within 5% of ideal):
  Count: 45
  Kappa: 7.91 ± 0.12
  Viscosity: 705 ± 8
  By digester:
  1    12
  2    18
  3    10
  4     5
```

### 3. Golden Batch DataFrame

```python
results['golden_batches']
# → DataFrame with all columns from master, filtered to golden zone
#   Columns: batch_id, digester, temp, pressure, ..., press1_kappa, press1_viscosity, ...
```

---

## ใช้ผลลัพธ์เพื่อ

### ✅ ตั้ง Operating Window
```python
# กำหนด Kappa & Viscosity ที่ดี เพื่อใช้ใน process control
kappa_window = (results['ideal_kappa'] - 0.3, results['ideal_kappa'] + 0.3)
viscos_window = (results['ideal_viscos'] - 25, results['ideal_viscos'] + 25)

# ติดตั้งบน control chart
```

### ✅ เทียบ Digester
```python
golden = results['golden_batches']
for dig in [1, 2, 3, 4]:
    subset = golden[golden['digester'] == dig]
    print(f"D{dig}: {len(subset)} golden batches, "
          f"Kappa {subset['press1_kappa'].mean():.2f}, "
          f"Viscosity {subset['press1_viscosity'].mean():.0f}")
```

**Result:** อาจเห็นว่า D2 มี golden batches มากสุด → "D2 is the golden digester"

### ✅ Step สำหรับ Workflow
```
Workflow.md Step 1–4:
  ✓ 01_build_master → batch_master.csv
  ✓ 02_analysis → Phase 1 (baseline) + ... + Pareto
  → ยังไปไม่ถึง "correlations X → Y" เพราะยังหา X params ไม่ได้
  → Pareto ให้ค่า target ก่อน
```

---

## Notes

1. **ฟังก์ชัน `pareto_frontier()` ปลอดภัยสำหรับ:**
   - NaN ต้อง drop ก่อน
   - Tied values (เช่น 2 batches มี Kappa=7.92) → ทั้งคู่อาจ on/off front
   - ข้อมูลไม่จำเป็นต้อง sorted

2. **เลือก Ideal vs Knee:**
   - `ideal_idx` = ใช้ Euclidean distance (ทำให้ง่าย)
   - `knee_idx` = ใช้ curvature (ยังไม่ implement ในโค้ด)
   - สำหรับ balanced trade-off → `ideal` พอ

3. **Golden threshold = 5%:**
   - ปรับได้ใน `pareto_golden_batch.py` line `golden_threshold = 0.05`
   - หรือ hardcode tolerance ตามใจเอง

---

## ตัวอย่างการใช้ (full example)

```python
# ในเซลล์ของ 02_analysis.ipynb
from pareto_golden_batch import analyze_pareto

# 1. Run analysis
results = analyze_pareto(master, lab_linked)

# 2. Get ideal values
ideal_kappa = results['ideal_kappa']
ideal_viscos = results['ideal_viscos']
print(f"Ideal Kappa: {ideal_kappa:.2f}, Viscosity: {ideal_viscos:.0f}")

# 3. Inspect golden batches
golden = results['golden_batches']
print(f"\nGolden batches summary:")
print(golden[['batch_id', 'digester', 'press1_kappa', 'press1_viscosity']].head(10))

# 4. Compare by digester
print(f"\nGolden by digester:")
for d in [1, 2, 3, 4]:
    g = golden[golden['digester'] == d]
    if len(g) > 0:
        print(f"D{d}: {len(g):<3} | Kappa {g['press1_kappa'].mean():.2f} | Viscosity {g['press1_viscosity'].mean():.0f}")

# 5. Next: use these values for operating window, process control, etc.
```

---

## Troubleshooting

| ปัญหา | สาเหตุ | แก้ไข |
|------|--------|------|
| `ImportError: pareto_golden_batch` | ไฟล์ไม่อยู่ในเดียวกัน | Check `pareto_golden_batch.py` ใน `Digester_Analysis/` |
| `KeyError: 'press1_kappa'` | lab_linked ไม่มี column | Check `load_outputs()` ว่าถูก map ไหม |
| 2-sigma filter ตัดเยอะ | Data มี outliers เยอะ | Check raw data, remove defects ก่อน |
| Pareto front มี 1 point | ข้อมูลแกร่งมากหรือ scale ต่างกัน | Normalize Kappa/Viscosity ก่อน |

---

## Next Steps

- [ ] Run `02_analysis.ipynb` ทั้งหมด (รวม Pareto cells)
- [ ] ตรวจสอบ `pareto_golden_batch.png`
- [ ] ใช้ ideal Kappa/Viscosity ตั้ง operating window
- [ ] ตัดสินใจ tolerance (±0.3 Kappa, ±25 Viscosity?) เพื่อ filter "near-golden"
- [ ] ใช้ golden batches เพื่อ analyze correlations with process X params
- [ ] Update `summaryUpdate.md` ด้วยผล
