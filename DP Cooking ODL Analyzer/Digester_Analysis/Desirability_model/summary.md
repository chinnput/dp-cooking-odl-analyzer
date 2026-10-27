# Desirability model - summary

Living status for the setpoint-optimization work. Update after every run.

## Goal

Find candidate digester setpoints (X) that push Press 1 quality (Y) toward target,
using a desirability function weighted toward Viscosity.

## Y targets (confirmed 2026-10-27)

| Y | shape | target | accept band | weight |
|---|---|---|---|---|
| Kappa | nominal-is-best | 9.2 | 9.0-9.5 | 1.0 |
| Viscosity | nominal-is-best | 750 | 700-800 | 2.0 (most important) |
| Brightness | - | not included yet | - | - |

Config in `desirability.py :: TARGETS`.

## Controllable X (optimizer tunes these)

`pfactor_setpoint`, `white_liquor_dosing_flow`, `circulation_temp` (hot liquor + cook),
`steam_to_heater_flow`, `LP_pressure`, `chip_weight`.
Config in `surrogate.py :: CONTROLLABLE` (one line each, easy to add/remove).

## Current state

- **Step 0 (gate): FAILED.** Process features cannot predict quality well enough.
  - Kappa: test R^2 RF = -0.13, Linear = 0.05 (n=450) -> worse than the mean.
  - Viscosity: test R^2 RF = 0.17, Linear = 0.20 (n=447) -> explains only ~17%.
- `desirability.py` verified (Kappa 9.2 -> d=1, Viscosity 750 -> d=1, one bad target sinks D).
- `01_optimize.ipynb` NOT built yet - optimizing on this model would give junk setpoints.
- `LP_pressure` now populated in the master (1529/1540) - can be added as a feature.
- **Per-digester check (2026-10-27): no gain.** Time-split R^2 Kappa < 0 in every set-up
  (pooled, pooled + Digester_ID, D1..D4 alone). Viscosity best = pooled Ridge 0.15.
  Kappa is mostly slow drift (59% of variance between days); batch setpoints barely
  move it within a digester. Viscosity drivers share the same sign in all 4 digesters.
- Steam flow tags unreliable (D1-D3 negative zero offset, D4 pegged at 21) - keep out.
- **Viscosity focus (2026-10-27):** best time-split R^2 0.11 (GBM pooled), gate not passed.
  Main driver alkali_accumulator1_conc (PM2.404AIC670, shared tag), ~ -16 Visc per g/l,
  partly monthly drift. Pooled > partial pooling > per digester.

## Decision

Do not optimize until the surrogate R^2 is acceptable. Improve the data/features first
(confounders, lag, causal X), then re-run the gate.
