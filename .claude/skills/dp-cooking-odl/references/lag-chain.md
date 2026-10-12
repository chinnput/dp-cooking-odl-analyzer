# Digester → Press 1 lag chain (PI AF), short version

Source: `DP Cooking ODL Analyzer/Pteam/Lag_Time_Sequence.md`, written in Thai with the full expressions. The logic runs in **PI AF**, `\\VPKGDCIPS01\iPMS`, element `PPPC_DP_Cooking`. **It is not in this repo's Python.** Ask the user for the AF expression before assuming anything not written here.

AF time arithmetic: `time + number` treats the number as seconds, and `time − time` gives seconds. Outputs marked "Map" are intermediate variables. They are not historized, so they can't be read back from PI.

| Step | Output | Logic |
|---|---|---|
| 1 | `Bn_Discharge_Timestamp` (T_D) | `FindEq('Bn_Current_Sequence','*-4h','*',"DISCHARGE")`. If not found, `'*'+2000`. |
| 2 | `Bn_Wait_Timestamp` (T_W) | The same for "WAIT". The search is not anchored to T_D (issue B). |
| 3 | `Bn_Discharge_Timeduration` (min) | Hour/Minute arithmetic, which breaks after crossing more than one hour (issue A). |
| 4 | `Time_Duration_Batch` (min) | `(MaxDischargeLevel/100 × 800 / AvgTotalDischargeFlow) × 60`. The tank is 800 m³. |
| 5 | `BnDischargeFinalTimestamp` (T_F) | `T_D + Time_Duration_Batch×60 + Timeduration×60` |
| 6 | `B1_DischargeStatus_FinalTime_Status_Rev`, `B2..B4_Discharge_FinalTime_Status` | Digester n is active in [T_D, T_F] under FIFO, so the oldest batch owns the tank. Uses the previous cycle's statuses as a state machine (issues C and E). |
| 7 | `LC_Chest_RetentionTime` | `(125 / LC Chest Outlet Flow) × 60` min + 5 min, converted to seconds |
| 8 | `Bn_Discharge_FinalTime_Press1_Status` | Step 6 status looked back by the Step 7 lag via `InterpolatedValues`, which produces fractions (issue G). The fix is `PrevVal`. |
| 9 | Notebook `Digester_ID` | Exact match `Bk == k`, otherwise NaN. Old issue I: "none" fell back to D1. |

Other issues: D (4-hour window truncates slow batches), F (the B1 output name `_Rev` differs from B2–B4), H (flow ≤ 0 gives a lag of 0 or a divide-by-zero, and low flow gives a huge lag).

**Fiber path (Line 2):** Batch 1–4 → Discharge tank 800 m³ → Screening → BSW → chest → **Press 1** → O2 Tank 1 (95 m³) → O2 Tank 2 (145 m³) → LC Chest 1 (110 m³) → Press 2 → LC Chest 2 (125 m³) → **Press 3** → Unbleached HD tower.

Open question: the Press 1 lag uses 125 m³, which equals the size of LC Chest 2. **Next goal:** an After-Press-3 lag chain (see section 5 of the source doc).
