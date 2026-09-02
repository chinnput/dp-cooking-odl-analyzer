"""
Step 3 & 4: Payload formatting and pushing data to AVEVA PI Server via Historical API endpoint (write_old).
"""

import time
from datetime import datetime, timedelta
import pandas as pd
import requests
import config


def prepare_pi_payloads(df_lab: pd.DataFrame) -> list:
    """
    Transforms wide lab DataFrame into a list of historical PI payload dictionaries.
    Payloads are strictly sorted in chronological order (oldest to newest timestamp).
    
    Schema matches write_old API expectations:
    {
        "tag": "...",
        "value": "...",
        "timestamp": "YYYY-MM-DD HH:MM:SS"
    }
    """
    if df_lab.empty:
        print("[Step 3] Warning: Input DataFrame is empty. No payloads created.")
        return []

    # 1. Sort DataFrame by Timestamp in chronological order (oldest first)
    df_sorted = df_lab.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)

    # 2. Build column map for mapped parameters
    col_to_tag = {}
    for param_key, tag_name in config.PI_TAG_MAPPING.items():
        for col in df_sorted.columns:
            if col == param_key or col.replace("_", "") == param_key.replace("_", ""):
                col_to_tag[col] = tag_name
                break

    payloads = []

    # 3. Iterate row-by-row chronologically
    for _, row in df_sorted.iterrows():
        ts = row["Timestamp"]
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)

        for col_name, tag_name in col_to_tag.items():
            val = row[col_name]
            if pd.notna(val):
                try:
                    val_float = float(val)
                    payload = {
                        "tag": tag_name,
                        "value": str(val_float),
                        "timestamp": ts_str
                    }
                    payloads.append(payload)
                except (ValueError, TypeError):
                    continue

    print(f"[Step 3] Prepared {len(payloads)} historical PI payload records in strict chronological order across {len(col_to_tag)} tag(s).")
    return payloads


def push_to_pi_server(payload_list: list, dry_run: bool = True, batch_size: int = 50, latest_timestamp=None) -> bool:
    """
    Sends historical data payloads to write_old API endpoint (http://10.28.58.72:8123/write_old)
    to write values directly into PI Tag archives at their exact historical timestamps.
    Prints detailed item-by-item logs to terminal during execution.
    """
    if not payload_list:
        print("[Step 3] No payloads to push.")
        return True

    total = len(payload_list)
    print(f"[Step 3] Processing {total} historical payload records (dry_run={dry_run})...\n")

    if dry_run:
        print("[Step 3] Dry-Run Mode active: Skipping actual HTTP POST requests.")
        print(f"[Step 3] Sample generated payload preview (first 20 of {total} items):\n")
        print("-" * 100)
        for i, p in enumerate(payload_list[:20], 1):
            print(f"  [{i}/{total}] {p['timestamp']} | Tag: {p['tag']:<30} | Value: {p['value']:<8} | [DRY-RUN]")
        print("-" * 100)
        print(f"\n[Step 3] Ready for live run! ({total} records prepared in strict chronological order).")
        return True

    # Live Execution Mode
    headers = {
        "Authorization": f"Bearer {config.WRITE_OLD_API_TOKEN}",
        "Content-Type": "application/json"
    }

    success_count = 0
    fail_count = 0
    pushed_items = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("-" * 100)
    for i, payload in enumerate(payload_list, 1):
        ts = payload.get('timestamp', '')
        tag = payload.get('tag', '')
        val = payload.get('value', '')

        try:
            response = requests.post(
                config.WRITE_OLD_API_URL,
                json=payload,
                headers=headers,
                timeout=15
            )

            if response.status_code in (200, 201):
                success_count += 1
                pushed_items.append({
                    "timestamp": ts,
                    "tag": tag,
                    "value": val,
                    "pushed_at": now_str
                })
                print(f"[{i}/{total}] {ts} | Tag: {tag:<30} | Value: {val:<8} | Status: {response.status_code} OK")
            else:
                fail_count += 1
                print(f"[{i}/{total}] {ts} | Tag: {tag:<30} | Value: {val:<8} | FAILED ({response.status_code}): {response.text}")

        except Exception as e:
            fail_count += 1
            print(f"[{i}/{total}] {ts} | Tag: {tag:<30} | Value: {val:<8} | EXCEPTION: {e}")

    print("-" * 100)
    print(f"[Step 3] Push completed. Total Success: {success_count}, Total Failed: {fail_count}")

    # Summary table of pushed items
    if pushed_items:
        print("\n📊 [Summary of Pushed Tags to PI Server]:")
        for item in pushed_items:
            print(f"  • {item['timestamp']} -> Tag: {item['tag']:<30} | Value: {item['value']}")
        print()

    # Update sync_state.json with latest timestamp and maintain 3-day history
    if config.SAVE_STATE and success_count > 0:
        from step1_fetch_onedrive import load_sync_state, save_sync_state
        state = load_sync_state()
        if latest_timestamp:
            state["last_sync_timestamp"] = str(latest_timestamp)

        # Append to 3-day rolling history
        history = state.get("pushed_history_3days", [])
        history.extend(pushed_items)

        # Filter out items older than 3 days
        cutoff_dt = datetime.now() - timedelta(days=3)
        filtered_history = []
        for h in history:
            try:
                h_ts = datetime.fromisoformat(h.get("timestamp", ""))
                if h_ts >= cutoff_dt:
                    filtered_history.append(h)
            except Exception:
                filtered_history.append(h)

        state["pushed_history_3days"] = filtered_history
        save_sync_state(state)
        print(f"[Step 3] Saved sync state (Last TS: {latest_timestamp}, 3-Day History: {len(filtered_history)} records).")

    return fail_count == 0


if __name__ == "__main__":
    from step1_fetch_onedrive import fetch_onedrive_data
    
    # Test Step 3 payload generation standalone
    df_lab = fetch_onedrive_data(check_state=False, save_state=False)
    if not df_lab.empty:
        payloads = prepare_pi_payloads(df_lab)
        push_to_pi_server(payloads, dry_run=True)

    from step1_fetch_onedrive import fetch_onedrive_data
    
    # Test Step 3 payload generation standalone
    df_lab = fetch_onedrive_data(check_state=False, save_state=False)
    if not df_lab.empty:
        payloads = prepare_pi_payloads(df_lab)
        push_to_pi_server(payloads, dry_run=True)

