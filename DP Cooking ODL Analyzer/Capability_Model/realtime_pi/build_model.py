"""
build_model.py  --  train the capability "boxes" ONCE and save them to boxes.json.

This is the TRAIN step of the separated realtime_pi workflow. It does NOT touch PI.

  train  = batches from batch_master.csv with batch_start <  --train-to  (a cutoff you pick)
  model  = per-digester boxes from cap.search() on that training slice
  saved  = boxes.json  (re-usable: fetch_current.py and backtest_oot.py load it,
           so neither rebuilds 71 boxes every run, and the model is reproducible)

Why save here instead of rebuilding in predict.predict():
  predict.predict() calls golden.load_golden() + cap.search() on the WHOLE file
  every time, mixing train and test. Here we freeze the model on data <= cutoff so
  an out-of-time backtest is honest (test batches never trained the model).

Run:
  python build_model.py                      # cutoff = default below
  python build_model.py --train-to 2026-10-01
  python build_model.py --train-to 2026-10-01 --out boxes_sep.json
"""

import argparse
import json
import os
import sys

import pandas as pd

# predict/golden/capability/config live one level up (the Capability_Model package).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config          # noqa: E402
import golden          # noqa: E402
import capability as cap   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "boxes.json")

# Default train cutoff. batch_master.csv currently ends 2026-10-18, so "train on
# everything up to 1 Oct, test on Oct" leaves a real out-of-time test set.
DEFAULT_TRAIN_TO = "2026-10-01"


def _boxes_for_digester(train, dg):
    """Build the boxes for ONE digester, the same way predict.predict(by_digester=True) does."""
    sub = train[train["digester"] == dg]
    xs = [c for c in config.CAP_X if c != "digester"]   # digester is fixed, not an X here
    res = cap.search(sub, xs=xs)
    return res


def build(train_to, out_path):
    """Train boxes on batches before `train_to`, save to `out_path`. Returns the saved dict."""
    # load_golden() applies the same row filters predict uses (both labs present,
    # viscosity spike filter, X_VALID_RANGE), and keeps batch_start so we can split by time.
    g = golden.load_golden()
    before = len(g)
    train = g[g["batch_start"] < train_to].reset_index(drop=True)
    print(f"train cutoff {train_to}: {len(train)}/{before} batches used for training "
          f"({train['batch_start'].min():%Y-%m-%d} .. {train['batch_start'].max():%Y-%m-%d})")

    digesters = sorted(int(d) for d in train["digester"].dropna().unique())
    model = {
        "train_to": str(train_to),
        "trained_on": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_train_batches": int(len(train)),
        "train_from": f"{train['batch_start'].min():%Y-%m-%d}",
        "train_last": f"{train['batch_start'].max():%Y-%m-%d}",
        "cap_x": config.CAP_X,
        "cap_spec": list(config.CAP_SPEC),
        "cap_spec2": list(config.CAP_SPEC2),
        "boxes_by_digester": {},
    }

    for dg in digesters:
        res = _boxes_for_digester(train, dg)
        if res is None or res.empty:
            print(f"  D{dg}: no boxes (too few batches)")
            model["boxes_by_digester"][str(dg)] = []
            continue
        # keep only what score()/consensus() need; rules -> list so JSON is clean
        recs = []
        for _, r in res.iterrows():
            recs.append({
                "combo": r["combo"],
                "rules": [[c, float(lo), float(hi)] for c, lo, hi in r["rules"]],
                "n": int(r["n"]),
                "visc_mean": float(r["visc_mean"]),
                "kappa_mean": float(r["kappa_mean"]),
                "cp_visc": float(r["cp_visc"]),
                "cp_kappa": float(r["cp_kappa"]),
                "cp_min": float(r["cp_min"]),
            })
        model["boxes_by_digester"][str(dg)] = recs
        print(f"  D{dg}: {len(recs)} boxes saved")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)
    print(f"saved model -> {out_path}")
    return model


def load_boxes(path=None):
    """Load a saved model and return (meta_dict, {digester:int -> res DataFrame})."""
    path = path or DEFAULT_OUT
    with open(path, encoding="utf-8") as f:
        model = json.load(f)
    by_dg = {}
    for dg, recs in model["boxes_by_digester"].items():
        rows = []
        for r in recs:
            rr = dict(r)
            rr["rules"] = [(c, lo, hi) for c, lo, hi in r["rules"]]  # back to tuples for score()
            rows.append(rr)
        by_dg[int(dg)] = pd.DataFrame(rows)
    return model, by_dg


def main():
    ap = argparse.ArgumentParser(description="Train capability boxes and save boxes.json.")
    ap.add_argument("--train-to", default=DEFAULT_TRAIN_TO,
                    help='train on batch_start < this date (YYYY-MM-DD). default %(default)s')
    ap.add_argument("--out", default=DEFAULT_OUT, help="output json path (default boxes.json)")
    args = ap.parse_args()
    build(args.train_to, args.out)


if __name__ == "__main__":
    main()
