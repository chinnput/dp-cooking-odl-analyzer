"""
realtime_pi/fetch_current.py  --  get the X of a just-finished batch and predict Y.

Flow:
    1. fetch_current(digester, start_time, end_time)  -> pull the batch's tags
       from PI and reduce each over its phase window.
       (or from_csv(path) if you already have a snapshot file).
    2. the X dict is scored against the SAVED model (boxes.json, built by
       build_model.py), NOT a model rebuilt on the whole file -- so realtime and
       the out-of-time backtest use the exact same boxes. run() prints which
       boxes the batch lands in + expected Y / cp.

ALL-DIGESTER MODE: run_all_digesters() loops D1-D4, fetches each one's latest
batch, predicts, and saves every result to results/predict_<timestamp>.csv +
.json as each digester finishes.

SAFETY: the agent does not run this (no PI access). The PI call is guarded by
ALLOW_PI_FETCH below -- it stays False until YOU set it True and run this file
yourself. from_csv() needs no PI and is safe to test anytime.

Run:  python fetch_current.py        (uses the manual demo example, no PI)
"""

import json
import os
import sys

import numpy as np
import pandas as pd

# make Capability_Model importable (predict.py, config.py live one level up)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import predict                          # noqa: E402  (Capability_Model/predict.py)
import config as cap_config             # noqa: E402  (Capability_Model/config.py)

import build_model                      # noqa: E402  (same folder: load_boxes)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")

# the saved model is loaded once and reused for every batch / digester
_MODEL_CACHE = None


def _load_model(path=None):
    """Load boxes.json once (cached). Returns (meta, {digester:int -> res DataFrame})."""
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        _MODEL_CACHE = build_model.load_boxes(path)
        meta = _MODEL_CACHE[0]
        print(f"loaded model: trained <= {meta['train_to']} on {meta['n_train_batches']} batches "
              f"({meta['train_from']} .. {meta['train_last']})")
    return _MODEL_CACHE

# realtime_pi/config.py (endpoint, tags). Works whether run as a script
# (python fetch_current.py) or imported as a package (realtime_pi.fetch_current).
try:
    from . import config as rt
except ImportError:
    # Run as a plain script: load realtime_pi/config.py directly under a UNIQUE
    # module name so it does NOT clash with Capability_Model/config.py (both are
    # named "config"; importing by name would return the already-cached top one).
    import importlib.util
    _rt_path = os.path.join(os.path.dirname(__file__), "config.py")
    _spec = importlib.util.spec_from_file_location("realtime_pi_config", _rt_path)
    rt = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(rt)        # type: ignore  # noqa: E402


# Hard safety switch. Keep False. Set True only when you run this yourself.
ALLOW_PI_FETCH = True


# ------------------------------------------------------------------ PI fetch
def _series(raw, tag, numeric=True):
    """Pull one tag's time series out of the MI Cube response as a DataFrame
    (columns: time, value). The API returns {"results": {tag: [{timestamp, value}]}}.
    numeric=False keeps text values (MAINSEQ phase names) instead of coercing to NaN."""
    records = raw.get(rt.RESPONSE_RESULTS_KEY, {}).get(tag, [])
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["time", "value"])
    df = df.rename(columns={rt.RESPONSE_TIME_KEY: "time",
                            rt.RESPONSE_VALUE_KEY: "value"})
    df["time"] = pd.to_datetime(df["time"])
    if numeric:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.sort_values("time")


def _phase_window(seq_df, phase):
    """
    Return (start, end) of the LAST contiguous run of `phase` in MAINSEQ.

    A wide fetch window can span more than one batch, so a phase (e.g. DISCHARGE)
    can appear twice. Taking min..max of all matching rows would merge two batches
    into one 6-hour "window". Instead split MAINSEQ into contiguous runs the same
    way batch.py does and keep the latest run of this phase = the just-finished batch.
    """
    if seq_df.empty:
        return None, None
    seq = seq_df.sort_values("time").reset_index(drop=True)
    norm = seq["value"].astype(str).str.strip().str.upper()
    run_id = (norm != norm.shift()).cumsum()          # new run whenever the phase text changes
    runs = seq.loc[norm == phase.upper()]
    if runs.empty:
        return None, None
    last_run = run_id.loc[runs.index].iloc[-1]         # the latest contiguous block of this phase
    block = seq.loc[run_id == last_run, "time"]
    return block.min(), block.max()


def _reduce(series_df, start, end, how):
    """Reduce a value series to one number over [start, end]."""
    if series_df.empty or start is None:
        return None
    w = series_df[(series_df["time"] >= start) & (series_df["time"] <= end)]["value"].dropna()
    if w.empty:
        return None
    if how == "max":
        return float(w.max())
    if how == "mean":
        return float(w.mean())
    if how == "last":
        return float(w.iloc[-1])
    raise ValueError(f"unknown reduce: {how}")


def fetch_current(digester, start_time, end_time):
    """
    Pull the finished batch (digester k, from chip-filling `start_time` to
    discharge `end_time`, plant local) from the MI Cube API and reduce each tag
    over its phase window into the X dict predict.predict() expects.

    Phase windows are sliced from the MAINSEQ text tag. pfactor_overshoot is
    computed as max(pfactor_actual over PREHYDRAU + HOT LIQUOR FILLING) minus
    pfactor_setpoint(last value in PREHYDRAU) -- matching the training definition
    in Digester_Analysis/prehydrolysis.py. digester is added directly.
    """
    if not ALLOW_PI_FETCH:
        raise RuntimeError(
            "PI fetch is disabled. Set ALLOW_PI_FETCH=True and run this file yourself. "
            "The agent must not call PI."
        )

    import requests  # local import so the module loads without the dep for from_csv()
    from dotenv import find_dotenv, load_dotenv
    load_dotenv(find_dotenv(usecwd=True))   # .env in the project root (same as Digester_Analysis)
    token = os.environ.get(rt.PI_TOKEN_ENV)
    if not token:
        raise RuntimeError(f"{rt.PI_TOKEN_ENV} not found in .env")

    k = int(digester)
    payload = dict(rt.PAYLOAD_TEMPLATE)
    payload["token"] = token
    payload["tags"] = rt.tags_for(k)
    payload["start_time"] = str(start_time)
    payload["end_time"] = str(end_time)

    resp = requests.post(rt.PI_ENDPOINT, json=payload, timeout=rt.PI_TIMEOUT)
    resp.raise_for_status()
    raw = resp.json()
    if raw.get("status") != "success":
        raise RuntimeError(f"MI Cube API error: {raw.get('message', raw)}")

    seq = _series(raw, rt.MAIN_SEQUENCE_TAG[k], numeric=False)   # MAINSEQ is phase text
    tag_lookup = {
        "CHIP_WEIGHT_TAG": rt.CHIP_WEIGHT_TAG.get(k),
        "ALKALI_CONC1_TAG": rt.ALKALI_CONC1_TAG,
        "PFACTOR_TEMP_SETPOINT_TAG": rt.PFACTOR_TEMP_SETPOINT_TAG.get(k),
        "PREHYD_MINUTES_TAG": rt.PREHYD_MINUTES_TAG.get(k),
    }

    x = {"digester": k}
    for col, (tag_name, phase, how) in rt.REDUCTION.items():
        tag = tag_lookup.get(tag_name)
        if not tag:                       # e.g. D1 has no P-temp setpoint tag
            continue
        s, e = _phase_window(seq, phase)
        x[col] = _reduce(_series(raw, tag), s, e, how)

    # Derived: pfactor_overshoot = max(pfactor over PREHYDRAU+HLF) - setpoint(last in PREHYDRAU)
    pf = _series(raw, rt.PFACTOR_ACTUAL_TAG[k])
    pf_sp = _series(raw, rt.PFACTOR_SETPOINT_TAG[k])
    prehyd_start, prehyd_end = _phase_window(seq, "PREHYDRAU")
    _, hlf_end = _phase_window(seq, "HOT LIQUOR FILLING")
    if prehyd_start is not None and hlf_end is not None:
        pfactor_final = _reduce(pf, prehyd_start, hlf_end, "max")          # over PREHYDRAU + HLF
        setpoint = _reduce(pf_sp, prehyd_start, prehyd_end, "last")        # last SP in PREHYDRAU
        if pfactor_final is not None and setpoint is not None:
            x["pfactor_overshoot"] = float(pfactor_final - setpoint)

    # When the batch was discharged (from MAINSEQ). Leading "_" keeps these out of
    # the X that score() reads; they are carried through to the saved result only.
    disch_start, disch_end = _phase_window(seq, "DISCHARGE")
    x["_discharge_start"] = str(disch_start) if disch_start is not None else None
    x["_discharge_end"] = str(disch_end) if disch_end is not None else None
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
def score_with_saved(x, model_path=None):
    """Score one X dict against the SAVED boxes for its digester. Returns (scored, consensus)."""
    _, boxes_by_dg = _load_model(model_path)
    dg = int(x["digester"]) if x.get("digester") is not None else None
    res = boxes_by_dg.get(dg)
    if res is None or res.empty:
        print(f"  no saved boxes for digester {dg}.")
        return pd.DataFrame(), predict.consensus(pd.DataFrame())
    scored = predict.score(res, x)
    return scored, predict.consensus(scored)


def _in_spec(y, spec):
    return pd.notna(y) and spec[0] <= y <= spec[1]


def run(x, model_path=None):
    """Score one X dict against the saved model and print the result."""
    scored, cons = score_with_saved(x, model_path)
    print("\nbatch X:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in x.items()})
    print("\nboxes this batch lands in (best cp first):")
    print(scored.to_string(index=False) if not scored.empty else "  (none)")
    print("\nconsensus prediction:")
    print(f"  Viscosity ~ {cons['visc_pred']}   Kappa ~ {cons['kappa_pred']}   "
          f"cp_min {cons['cp_min']}   from {cons['n_boxes']} boxes / {cons['n_batches']} batches")
    return scored, cons


def _result_row(digester, x, cons, predicted_at=None):
    """One flat record (X + prediction + in-spec flags) for the saved results file."""
    row = {
        "digester": digester,
        "discharge_start": x.get("_discharge_start"),   # when the batch was discharged (from MAINSEQ)
        "discharge_end": x.get("_discharge_end"),
        "predicted_at": predicted_at,                   # when this prediction was computed
    }
    row.update({c: (round(x[c], 2) if isinstance(x.get(c), float) else x.get(c))
                for c in cap_config.CAP_X if c != "digester"})
    row.update({
        "visc_pred": cons["visc_pred"],
        "visc_in_spec": _in_spec(cons["visc_pred"], cap_config.CAP_SPEC),
        "kappa_pred": cons["kappa_pred"],
        "kappa_in_spec": _in_spec(cons["kappa_pred"], cap_config.CAP_SPEC2),
        "cp_min": cons["cp_min"],
        "n_boxes": cons["n_boxes"],
        "n_batches": cons["n_batches"],
    })
    return row


def _json_safe(v):
    """NaN/inf -> None so the JSON is valid (standard JSON has no NaN)."""
    if isinstance(v, float) and not np.isfinite(v):
        return None
    return v


def _save_results(rows, stamp):
    """Write the per-digester predictions to results/predict_<stamp>.csv + .json."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    df = pd.DataFrame(rows)
    csv_path = os.path.join(RESULTS_DIR, f"predict_{stamp}.csv")
    json_path = os.path.join(RESULTS_DIR, f"predict_{stamp}.json")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    clean = [{k: _json_safe(v) for k, v in row.items()} for row in rows]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2, default=str, allow_nan=False)
    print(f"\nsaved -> {csv_path}")
    print(f"saved -> {json_path}")
    return csv_path, json_path


def run_all_digesters(windows, model_path=None):
    """
    Predict every digester's latest batch, saving each result as it finishes.

    windows : {digester: (start_time, end_time)} for the finished batch of each D.
              Omit a digester to skip it.
    Each digester is fetched from PI, scored against the saved model, printed, and
    appended to results/predict_<timestamp>.{csv,json}. A failed digester is logged
    and skipped (the rest still run and save).
    """
    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    rows = []
    for k in sorted(windows):
        start_time, end_time = windows[k]
        print(f"\n===== Digester D{k}  ({start_time} .. {end_time}) =====")
        predicted_at = str(pd.Timestamp.now())
        try:
            x = fetch_current(k, start_time, end_time)
            _, cons = run(x, model_path)
            rows.append(_result_row(k, x, cons, predicted_at))
        except Exception as e:                       # one digester failing must not stop the rest
            print(f"  D{k} FAILED: {e}")
            rows.append({"digester": k, "predicted_at": predicted_at, "error": str(e)})
        _save_results(rows, stamp)                   # save after each D, so partial progress persists
    print(f"\ndone: {sum('error' not in r for r in rows)}/{len(rows)} digesters predicted.")
    return rows


if __name__ == "__main__":
    # --- ALL digesters: give each finished batch's (start, end), predict + save ---
    # Fill the window of the latest finished batch per digester. Omit any you don't
    # want to run. Each result is written to results/predict_<timestamp>.{csv,json}.
    WINDOWS = {
        1: ("2026-11-04 06:00:00", "2026-11-04 18:00:00"),
        2: ("2026-11-04 06:00:00", "2026-11-04 18:00:00"),
        3: ("2026-11-04 06:00:00", "2026-11-04 18:00:00"),
        4: ("2026-11-04 06:00:00", "2026-11-04 18:00:00"),
    }
    run_all_digesters(WINDOWS)
