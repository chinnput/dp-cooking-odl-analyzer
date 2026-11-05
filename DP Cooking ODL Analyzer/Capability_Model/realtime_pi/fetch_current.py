"""
realtime_pi/fetch_current.py  --  get the X of a just-finished batch and predict Y.

Flow:
    1. fetch_current(digester, discharge_time)  -> pull the X tags from PI
       (or from_csv(path) if you already have a snapshot file).
    2. the X dict is handed to predict.predict(), which scores it against the
       historical boxes and prints: which boxes it lands in + expected Y / cp.

SAFETY: the agent does not run this (no PI access). The PI call is guarded by
ALLOW_PI_FETCH below -- it stays False until YOU set it True and run this file
yourself. from_csv() needs no PI and is safe to test anytime.

Run:  python fetch_current.py        (uses the demo CSV path / manual example)
"""

import os
import sys

import pandas as pd

# make Capability_Model importable (predict.py, config.py live one level up)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import predict                          # noqa: E402  (Capability_Model/predict.py)
import config as cap_config             # noqa: E402  (Capability_Model/config.py)

# realtime_pi/config.py (endpoint, tags). Works whether run as a script
# (python fetch_current.py) or imported as a package (realtime_pi.fetch_current).
try:
    from . import config as rt
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    import config as rt                 # type: ignore  # noqa: E402


# Hard safety switch. Keep False. Set True only when you run this yourself.
ALLOW_PI_FETCH = False


# ------------------------------------------------------------------ PI fetch
def fetch_current(digester, discharge_time):
    """
    Pull the final X of the batch that just discharged from `digester` at
    `discharge_time` (plant local). Returns a dict keyed by batch_master column,
    ready for predict.predict().

    This is a SKELETON. The actual request/response parsing must match the real
    MI Cube API -- compare rt.PAYLOAD_TEMPLATE / rt.RESPONSE_*_KEY to the API doc
    or to Lab_Analysis's working call, then finish the TODOs.
    """
    if not ALLOW_PI_FETCH:
        raise RuntimeError(
            "PI fetch is disabled. Set ALLOW_PI_FETCH=True and run this file yourself. "
            "The agent must not call PI."
        )

    import requests  # local import so the module loads without the dep for from_csv()
    from dotenv import load_dotenv
    load_dotenv()
    token = os.environ.get(rt.PI_TOKEN_ENV)
    if not token:
        raise RuntimeError(f"{rt.PI_TOKEN_ENV} not found in .env")

    k = int(digester)
    tags = [t.format(k=k) for t in rt.TAG_MAP.values()]
    tags += [t.format(k=k) for t in rt.DERIVED_RAW_TAGS.values()]

    payload = dict(rt.PAYLOAD_TEMPLATE)
    payload["tags"] = tags
    payload["startTime"] = str(discharge_time)
    payload["endTime"] = str(discharge_time)

    # TODO: confirm method (GET vs POST), header format, and param names.
    resp = requests.post(
        rt.PI_ENDPOINT,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=rt.PI_TIMEOUT,
    )
    resp.raise_for_status()
    raw = resp.json()

    # TODO: map raw PI tag values back to batch_master columns, and compute the
    # DERIVED X (pfactor_overshoot, prehydrolysis_minutes) the same way
    # prehydrolysis.py does. Placeholder parse below:
    values = {item[rt.RESPONSE_TAG_KEY]: item[rt.RESPONSE_VALUE_KEY] for item in raw}
    x = {"digester": k}
    for col, tag in rt.TAG_MAP.items():
        x[col] = values.get(tag.format(k=k))
    # x["pfactor_overshoot"] = ...        # compute from pfactor_calc at prehyd vs HLF end
    # x["prehydrolysis_minutes"] = ...     # compute from sequence_step timestamps
    return x


# ------------------------------------------------------------------ CSV input
def from_csv(path, row=-1):
    """
    Load one finished batch's X from a CSV snapshot (one row per batch, columns =
    batch_master column names). row=-1 = the last row. No PI needed. Good for
    testing the whole pipeline before wiring PI.
    """
    df = pd.read_csv(path)
    r = df.iloc[row]
    return {c: r[c] for c in cap_config.CAP_X if c in df.columns}


# ------------------------------------------------------------------ predict
def run(x):
    """Score one X dict and print the result."""
    scored, cons = predict.predict(x)
    print("\nbatch X:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in x.items()})
    print("\nboxes this batch lands in (best cp first):")
    print(scored.to_string(index=False) if not scored.empty else "  (none)")
    print("\nconsensus prediction:")
    print(f"  Viscosity ~ {cons['visc_pred']}   Kappa ~ {cons['kappa_pred']}   "
          f"cp_min {cons['cp_min']}   from {cons['n_boxes']} boxes / {cons['n_batches']} batches")
    return scored, cons


if __name__ == "__main__":
    # Demo with a manual X (no PI). Replace with fetch_current(...) when wired.
    demo_x = {
        "pfactor_overshoot": 40,
        "alkali_accumulator1_conc_mean_hot_liquor_filling": 95,
        "prehydrolysis_minutes": 70,
        "chip_weight_max_chip_filling": 36,
        "digester": 3,
        "pfactor_temp_setpoint_last_prehydrolysis": 165,
    }
    run(demo_x)
