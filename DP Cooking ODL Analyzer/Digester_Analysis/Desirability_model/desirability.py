"""
Desirability functions (Derringer-Suich) for DP cooking quality.

One d_i per target in [0, 1] (0 = unacceptable, 1 = on target), combined into a
single weighted geometric mean D. Viscosity is weighted highest on purpose.

d shapes used here:
  - target (nominal-is-best): peak at `target`, ramps to 0 at low / high bounds.
  - larger-is-better: 0 at `low`, 1 at `target` and above.

Pure functions, no I/O. Import and reuse from the notebooks.
"""
import numpy as np

# ---- Target config (edit here). weight: higher = more important in D.
# shape "target" -> (low, target, high). shape "larger" -> (low, target).
TARGETS = {
    "press1_kappa": {"shape": "target", "low": 8.0, "target": 9.8, "high": 10.5, "weight": 1.0},
    "press1_viscosity": {"shape": "target", "low": 700.0, "target": 750.0, "high": 800.0, "weight": 2.0},
}


def d_target(y, low, target, high):
    """Nominal-is-best: 0 outside [low, high], 1 at target, linear in between."""
    y = np.asarray(y, dtype=float)
    d = np.zeros_like(y)
    up = (y > low) & (y <= target)
    down = (y > target) & (y < high)
    d[up] = (y[up] - low) / (target - low)
    d[down] = (high - y[down]) / (high - target)
    return d


def d_larger(y, low, target):
    """Larger-is-better: 0 at/below low, 1 at/above target, linear in between."""
    y = np.asarray(y, dtype=float)
    d = np.clip((y - low) / (target - low), 0.0, 1.0)
    return d


def desirability_one(y, spec):
    """d_i for one target given its spec dict from TARGETS."""
    if spec["shape"] == "larger":
        return d_larger(y, spec["low"], spec["target"])
    return d_target(y, spec["low"], spec["target"], spec["high"])


def overall_desirability(values, targets=TARGETS):
    """
    Weighted geometric mean of the per-target d_i.

        D = (prod d_i ** w_i) ** (1 / sum w_i)

    `values` maps each target column name to a scalar or array of Y predictions.
    Any d_i == 0 forces D == 0 (one bad target sinks the batch), matching the
    overall_grade logic. Returns a float or array aligned with the inputs.
    """
    ds, ws = [], []
    for col, spec in targets.items():
        if col not in values:
            continue
        ds.append(np.clip(desirability_one(values[col], spec), 1e-9, 1.0))
        ws.append(spec["weight"])
    if not ds:
        raise ValueError("no matching target columns in values")
    ds = np.vstack([np.atleast_1d(d) for d in ds])
    ws = np.asarray(ws).reshape(-1, 1)
    logd = (ws * np.log(ds)).sum(axis=0) / ws.sum()
    D = np.exp(logd)
    return D.item() if D.size == 1 else D
