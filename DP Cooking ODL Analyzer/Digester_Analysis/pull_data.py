# Pull tags from PI (MI Cube API) and save them to data/ as one table.
# Run by the user:   python pull_data.py
# The analysis notebook only reads the saved file, it does not pull again.

import os
import pandas as pd
import requests
from dotenv import find_dotenv, load_dotenv

import config

load_dotenv(find_dotenv(usecwd=True))  # .env in the project root


def pull_chunk(tags, start, end, interval):
    """Pull one time chunk. Returns a long table: timestamp, tag, value."""
    payload = {
        "token": os.environ["MI_CUBE_API_TOKEN"],
        "server": config.PI_SERVER,
        "tags": tags,
        "start_time": str(start),
        "end_time": str(end),
        "interval": interval,
    }
    response = requests.post(config.MI_CUBE_API_URL, json=payload, timeout=300)
    data = response.json()
    if data.get("status") != "success":
        print(f"  Failed: {data.get('message')}")
        return pd.DataFrame()

    rows = []
    for tag, records in data["results"].items():
        for r in records:
            rows.append({"timestamp": r["timestamp"], "tag": tag, "value": r["value"]})
    return pd.DataFrame(rows)


def pull_tags(tags, start, end, interval, chunk_days=7):
    """Pull all tags chunk by chunk. Returns a wide table: one column per tag."""
    chunk_starts = pd.date_range(start, end, freq=f"{chunk_days}D")
    parts = []
    for chunk_start in chunk_starts:
        chunk_end = min(chunk_start + pd.Timedelta(days=chunk_days), pd.Timestamp(end))
        print(f"Pulling {chunk_start} -> {chunk_end} ...")
        part = pull_chunk(tags, chunk_start, chunk_end, interval)
        print(f"  {len(part)} values")
        parts.append(part)

    df = pd.concat(parts, ignore_index=True)

    # MI Cube labels timestamps "+00:00" but they are local plant time -> drop the label only
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)

    # Long -> wide (one row per timestamp, one column per tag)
    df = df.drop_duplicates(["timestamp", "tag"])
    wide = df.pivot(index="timestamp", columns="tag", values="value").sort_index()

    # Numbers to float; text tags (phase sequence, digital valves) stay as text
    text_tags = config.text_tags()
    for col in wide.columns:
        if col not in text_tags:
            wide[col] = pd.to_numeric(wide[col], errors="coerce")
    return wide


def save_data(df, name):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    path = os.path.join(config.DATA_DIR, f"{name}.csv.gz")
    df.to_csv(path)
    print(f"Saved {len(df)} rows -> {path}")


def load_data(name):
    path = os.path.join(config.DATA_DIR, f"{name}.csv.gz")
    return pd.read_csv(path, index_col="timestamp", parse_dates=True)


if __name__ == "__main__":
    tags = config.all_tags()
    print(f"Tags: {len(tags)} | {config.START_TIME} -> {config.END_TIME} | interval {config.INTERVAL}")

    df = pull_tags(tags, config.START_TIME, config.END_TIME, config.INTERVAL, config.CHUNK_DAYS)
    df = df.rename(columns=config.tag_to_name())   # PI tag -> friendly name (D1_temp, ...)

    name = f"digester_{config.START_TIME[:10]}_{config.END_TIME[:10]}"
    save_data(df, name)
