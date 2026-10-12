import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from step1_fetch_onedrive import fetch_onedrive_data
from step2_time_matching import process_lab_data
from step3_pi_api_client import prepare_pi_payloads

if __name__ == '__main__':
    print('Loading Excel files...')
    df = fetch_onedrive_data(process_all_files=True)
    print('Total extracted rows:', len(df))

    proc = process_lab_data(df, mode='hourly')
    print('Processed rows for hourly:', len(proc))

    payloads = prepare_pi_payloads(proc)
    print('Total payloads prepared:', len(payloads))

    print('\nSample payloads (first 30):')
    for p in payloads[:30]:
        print(json.dumps(p, ensure_ascii=False))

    if len(payloads) > 30:
        print('\n... (truncated)')
