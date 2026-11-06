"""
backtest_oot.py  --  out-of-time backtest: test the SAVED model on later batches.

This is the TEST step of the separated realtime_pi workflow. It does NOT touch PI:
both the test X and the real lab Y come from batch_master.csv.

  model  = boxes.json  (trained by build_model.py on batch_start <  train_to)
  test   = batches from batch_master.csv with  train_to <= batch_start < test_to
  for each test batch:
      X (from CSV) -> score against its digester's saved boxes -> consensus prediction
      compare prediction to the batch's REAL lab Y (from CSV, more accurate than PI)
  output = results/backtest_<range>.csv        (one row per batch)
           results/backtest_<range>_summary.json (MAE, spec agreement, N per digester)

Run (after build_model.py):
  python backtest_oot.py                       # test = everything from train_to onward
  python backtest_oot.py --test-to 2026-11-01  # cap the test window
  python backtest_oot.py --model boxes_sep.json
"""

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config          # noqa: E402
import golden          # noqa: E402
import predict         # noqa: E402

import build_model     # noqa: E402  (same folder)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")


def _in_spec(y, spec):
    return spec[0] <= y <= spec[1]


def _mape(true, pred):
    """Mean absolute percentage error (%). Skips rows where true == 0."""
    true, pred = np.asarray(true, dtype=float), np.asarray(pred, dtype=float)
    m = true != 0
    if not m.any():
        return np.nan
    return float(np.mean(np.abs((true[m] - pred[m]) / true[m])) * 100)


def _r2(true, pred):
    """Coefficient of determination. <0 means worse than predicting the mean."""
    true, pred = np.asarray(true, dtype=float), np.asarray(pred, dtype=float)
    ss_tot = float(np.sum((true - true.mean()) ** 2))
    if ss_tot == 0:
        return np.nan
    ss_res = float(np.sum((true - pred) ** 2))
    return float(1 - ss_res / ss_tot)


def _none_if_nan(v, ndigits):
    return None if v != v else round(float(v), ndigits)


def _fmt_pct(v):
    return "n/a" if v is None else f"{v:.1f}%"


def _fmt_num(v):
    return "n/a" if v is None else f"{v:.3f}"


def run(model_path=None, test_to=None):
    model, boxes_by_dg = build_model.load_boxes(model_path)
    train_to = model["train_to"]
    print(f"model: trained <= {train_to} on {model['n_train_batches']} batches "
          f"({model['train_from']} .. {model['train_last']})")

    g = golden.load_golden()
    test = g[g["batch_start"] >= train_to]
    if test_to:
        test = test[test["batch_start"] < test_to]
    test = test.dropna(subset=[config.CAP_TARGET, config.CAP_TARGET2]).reset_index(drop=True)
    if test.empty:
        print("no test batches after the cutoff; nothing to backtest.")
        return
    print(f"test window: {len(test)} batches "
          f"({test['batch_start'].min():%Y-%m-%d} .. {test['batch_start'].max():%Y-%m-%d})")

    xs_cols = list(config.CAP_X)
    rows = []
    for _, b in test.iterrows():
        dg = int(b["digester"]) if pd.notna(b["digester"]) else None
        res = boxes_by_dg.get(dg)
        x = {c: b[c] for c in xs_cols if c in test.columns}
        if res is None or res.empty:
            c = {"visc_pred": np.nan, "kappa_pred": np.nan, "cp_min": np.nan,
                 "n_boxes": 0, "n_batches": 0}
        else:
            c = predict.consensus(predict.score(res, x))
        rows.append({
            "batch_id": b.get("batch_id"),
            "digester": dg,
            "batch_start": f"{b['batch_start']:%Y-%m-%d %H:%M}",
            "visc_true": round(float(b[config.CAP_TARGET]), 1),
            "visc_pred": c["visc_pred"],
            "visc_err": (round(abs(b[config.CAP_TARGET] - c["visc_pred"]), 1)
                         if pd.notna(c["visc_pred"]) else np.nan),
            "kappa_true": round(float(b[config.CAP_TARGET2]), 2),
            "kappa_pred": c["kappa_pred"],
            "kappa_err": (round(abs(b[config.CAP_TARGET2] - c["kappa_pred"]), 2)
                          if pd.notna(c["kappa_pred"]) else np.nan),
            "cp_min": c["cp_min"],
            "n_boxes": c["n_boxes"],
        })

    out = pd.DataFrame(rows)
    covered = out[out["visc_pred"].notna()].copy()
    n, n_cov = len(out), len(covered)

    summary = {
        "model_train_to": train_to,
        "test_from": f"{test['batch_start'].min():%Y-%m-%d}",
        "test_to": f"{test['batch_start'].max():%Y-%m-%d}",
        "n_test": n,
        "n_covered": n_cov,
        "coverage": round(n_cov / n, 3) if n else 0.0,
    }

    if n_cov:
        vt, vp = covered["visc_true"].to_numpy(), covered["visc_pred"].to_numpy()
        kt, kp = covered["kappa_true"].to_numpy(), covered["kappa_pred"].to_numpy()
        mae_v, mae_k = float(np.mean(np.abs(vt - vp))), float(np.mean(np.abs(kt - kp)))
        base_v = float(np.mean(np.abs(vt - vt.mean())))   # predict-the-mean baseline
        base_k = float(np.mean(np.abs(kt - kt.mean())))
        mape_v, mape_k = _mape(vt, vp), _mape(kt, kp)     # % off, guards true==0
        r2_v, r2_k = _r2(vt, vp), _r2(kt, kp)             # fraction of variance explained
        visc_agree = float(np.mean([_in_spec(a, config.CAP_SPEC) == _in_spec(p, config.CAP_SPEC)
                                    for a, p in zip(vt, vp)]))
        kappa_agree = float(np.mean([_in_spec(a, config.CAP_SPEC2) == _in_spec(p, config.CAP_SPEC2)
                                     for a, p in zip(kt, kp)]))
        summary.update({
            "mae_visc": round(mae_v, 1), "base_visc": round(base_v, 1),
            "visc_beats_baseline": mae_v < base_v,
            "visc_mape_pct": _none_if_nan(mape_v, 1),
            "visc_accuracy_pct": _none_if_nan(100 - mape_v if mape_v == mape_v else np.nan, 1),
            "visc_r2": _none_if_nan(r2_v, 3),
            "mae_kappa": round(mae_k, 2), "base_kappa": round(base_k, 2),
            "kappa_beats_baseline": mae_k < base_k,
            "kappa_mape_pct": _none_if_nan(mape_k, 1),
            "kappa_accuracy_pct": _none_if_nan(100 - mape_k if mape_k == mape_k else np.nan, 1),
            "kappa_r2": _none_if_nan(r2_k, 3),
            "visc_spec_agreement": round(visc_agree, 3),
            "kappa_spec_agreement": round(kappa_agree, 3),
            "per_digester": {
                str(dg): int((covered["digester"] == dg).sum())
                for dg in sorted(covered["digester"].dropna().unique())
            },
        })

    # save
    os.makedirs(RESULTS_DIR, exist_ok=True)
    tag = f"{summary['test_from']}_to_{summary['test_to']}"
    csv_path = os.path.join(RESULTS_DIR, f"backtest_{tag}.csv")
    json_path = os.path.join(RESULTS_DIR, f"backtest_{tag}_summary.json")
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # report
    print(f"\nbacktest {tag}:")
    print(f"  covered {n_cov}/{n} ({summary['coverage']:.0%}) test batches fell into >=1 saved box")
    if n_cov:
        print(f"  Viscosity MAE {summary['mae_visc']:6.1f}  vs baseline {summary['base_visc']:6.1f}  "
              f"({'BETTER' if summary['visc_beats_baseline'] else 'worse'})")
        print(f"  Kappa     MAE {summary['mae_kappa']:6.2f}  vs baseline {summary['base_kappa']:6.2f}  "
              f"({'BETTER' if summary['kappa_beats_baseline'] else 'worse'})")
        print(f"  Viscosity accuracy {_fmt_pct(summary['visc_accuracy_pct'])} "
              f"(MAPE {_fmt_pct(summary['visc_mape_pct'])})  R2 {_fmt_num(summary['visc_r2'])}")
        print(f"  Kappa     accuracy {_fmt_pct(summary['kappa_accuracy_pct'])} "
              f"(MAPE {_fmt_pct(summary['kappa_mape_pct'])})  R2 {_fmt_num(summary['kappa_r2'])}")
        print(f"  Viscosity spec agreement {summary['visc_spec_agreement']:.0%}  "
              f"Kappa spec agreement {summary['kappa_spec_agreement']:.0%}")
    print(f"saved -> {csv_path}")
    print(f"saved -> {json_path}")
    return out, summary


def main():
    ap = argparse.ArgumentParser(description="Out-of-time backtest of the saved boxes.json.")
    ap.add_argument("--model", default=None, help="model json path (default boxes.json)")
    ap.add_argument("--test-to", default=None,
                    help="test on batch_start < this date (YYYY-MM-DD). default = all after cutoff")
    args = ap.parse_args()
    run(args.model, args.test_to)


if __name__ == "__main__":
    main()
