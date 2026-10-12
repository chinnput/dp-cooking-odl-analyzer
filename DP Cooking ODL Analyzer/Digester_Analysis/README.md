# Digester_Analysis

Batch-level analysis of digesters D1–D4: phases, H-factor, and how much each value varies from batch to batch.

## Files

| File | What it does |
|---|---|
| `config.py` | WHAT to pull: tags per digester, shared chemical tags, time range, interval |
| `pull_data.py` | Pulls the tags from PI (MI Cube API) and saves them to `data/` |
| `batch.py` | Splits the timeline into phases and batches using the MAINSEQ tag |
| `hfactor.py` | H-factor functions |
| `digester_analysis.ipynb` | Loads the saved data, builds the batch table and H-factor, then plots |
| `data/` | Saved pulls (git-ignored) |

## How to run

1. Check the tags and time range in `config.py`. Two tags are marked `TO VERIFY`.
2. Pull the data once (this needs `MI_CUBE_API_TOKEN` in the root `.env`):
   ```
   cd "DP Cooking ODL Analyzer/Digester_Analysis"
   python pull_data.py
   ```
3. Open `digester_analysis.ipynb` and run all cells. It only reads `data/`.

## Notes

- Use a 1-minute interval. The temperature ramps quickly, and a coarser interval misses part of the H-factor.
- MI Cube timestamps are labelled `+00:00`, but they are local plant time. `pull_data.py` removes the label without converting.
- `batch_id` starts a new batch at every CHIP FILLING. `batch_no` is the DCS batch number, kept for reference.
- The H-factor uses the `HEAT&COOK` phase by default (`H_FACTOR_PHASES` in config).
