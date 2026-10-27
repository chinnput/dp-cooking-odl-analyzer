# Desirability model - workflow

## Pipeline

```
Step 0  surrogate model   X -> Y      fit, check test R^2   (GATE)
Step 1  desirability      Y -> d_i    per-target score 0..1
Step 2  combine           d_i -> D    weighted geo-mean
Step 3  optimizer         find X* that maximizes D within data-range bounds
```

Step 0 is a gate: if R^2 is too low, STOP - steps 1-3 would optimize on noise.

## Files

| File | Type | Role |
|---|---|---|
| `desirability.py` | py | d_i shapes + weighted D. Pure functions. |
| `surrogate.py` | py | fit Linear/RF per target, report R^2 + importance. Edit `CONTROLLABLE` here. |
| `00_model_check.ipynb` | nb | run the gate, show R^2 + feature importance. |
| `01_optimize.ipynb` | nb | (build only after gate passes) desirability + optimizer + contour. |
| `summary.md` | md | current status, targets, latest R^2. |
| `update.md` | md | dated log (What / Results / Found by). |

Why py + nb: logic that is reused or tested lives in `.py` (same as `config.py`,
`batch.py`, `build_master.py`); notebooks only run and visualize.

## Desirability formulas

Per target, d_i in [0, 1]:

- **nominal-is-best** (Kappa, Viscosity): 0 outside [low, high], 1 at target, linear in between.
- **larger-is-better**: 0 at low, 1 at target and above.

Overall (weighted geometric mean):

    D = ( prod_i d_i^w_i ) ^ ( 1 / sum_i w_i )

Any d_i = 0 forces D = 0 (one bad target sinks the batch) - matches `overall_grade`.
Viscosity weight 2 vs Kappa 1, so D leans toward Viscosity.

## Rules / caveats

- **Gate first.** No optimization while surrogate R^2 is weak.
- **Correlation != causation.** Observational data, confounders not removed
  (time trend, production rate, lag). Results are hypotheses, not commands.
- **X must be truly controllable.** Optimizer tunes `CONTROLLABLE` only - setpoints
  the operators can set, not derived effects (h_factor, white_liquor_m3).
- **No extrapolation.** Clamp optimizer bounds to the observed data range per X.
- **Output = candidate setpoints for a trial run**, to be confirmed on the plant.
- Read-only on local data. Never pull PI here - ask the user to re-pull.
