# Paper / Board Machine Context

Use as a checklist of hypotheses, not as facts about the user's specific machine. Always confirm with the user's engineers and data.

## Typical quality variables (Y)

- **Reel/QCS (online, scanner)**: basis weight (grammage), moisture, caliper; MD and CD profiles (2σ of CD profile is a standard metric).
- **Lab (per reel/set)**: tensile (MD/CD), burst, ring crush (RCT), short-span compression (SCT), CMT/concora (fluting), Cobb (water absorption), porosity/air permeance, smoothness/roughness, brightness/color, ply bond / Scott bond, dirt count, curl.
- Strength indices often normalized by basis weight (e.g., SCT index = SCT/grammage) — compare indices, not raw strength, across grades.

## Typical drivers (X)

- **Stock prep**: refining specific energy (kWh/t), freeness/CSF or SR, fiber mix (OCC vs virgin %, recycled ratio), raw material batch/supplier, ash/filler content, contaminants.
- **Chemistry**: starch (surface/wet-end) dosage, retention aids, sizing agents (AKD/ASA), pH, conductivity, charge (zeta potential), temperature.
- **Wet end**: headbox consistency, jet-to-wire ratio (rush/drag), slice opening, headbox pressure, white-water consistency, first-pass retention, vacuum levels.
- **Press section**: nip loads, felt condition/age, steam box, press dryness.
- **Dryer section**: steam pressure per group, dryer hood temperature/humidity, sheet temperature.
- **Size press / calender**: starch solids and pickup, calender load, temperature.
- **Machine**: speed, production rate (t/h), wire and felt age (days since change), sheet breaks.
- **Environment**: ambient temperature/humidity, season (affects drying and fiber).

## Things that commonly create misleading results

- **Grade/grammage differences** dominate everything — analyze per grade or use indices.
- **QCS control loops**: basis weight and moisture are actively controlled (stock flow, steam). Their actuators move to *compensate*, so correlations reflect the controller, not physics. Analyze controller output (e.g., steam demand) as a symptom.
- **Lags**: stock prep → reel can be minutes to tens of minutes; lab results are reported after the reel is done. Align by reel ID if available.
- **Felt/wire life**: slow drift over days/weeks → shows as Pp ≪ Cp; include "days since clothing change" as an X.
- **Raw material variability** (recycled fiber quality) often the biggest uncontrollable driver — capture via freeness, ash, or supplier/lot.

## Useful derived features

- Specific refining energy = refiner power / fiber flow.
- Strength indices (per grammage).
- Days since felt/wire change; time since grade change.
- Rolling std of key X (process instability as a driver of Y variability, not just mean).
- Ratios: jet/wire, OCC share, starch per ton.

## Link to effectiveness (OPE/OEE)

Quality gaps also appear as losses: off-spec/downgraded tonnage, broke, sheet breaks, grade-change time. When optimizing, quantify gains in those units too (t/day recovered, % broke reduced), not only Cpk.
