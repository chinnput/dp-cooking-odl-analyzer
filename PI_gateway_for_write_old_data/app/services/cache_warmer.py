import time
import pandas as pd
import os
from datetime import datetime, timedelta
from app.services.pi_service import pi_service

# Configuration
WARM_PERIOD_DAYS = 2

def warm_active_tags():
    """
    Finds tags used in the last 2 days and refreshes their cache using CSV stats.
    """
    print(f"[{datetime.now()}] Ticker: Starting Cache Warmup...")
    
    # Auto-cleanup CSV cache older than 7 days
    pi_service.cleanup_old_csv_cache(days=7)
    
    if not os.path.exists(pi_service.stats_file):
        print("Ticker: No stats file found. Skipping.")
        return

    try:
        # 1. Find Active Tags from CSV
        df_stats = pd.read_csv(pi_service.stats_file)
        if df_stats.empty:
            print("Ticker: No stats yet. Skipping.")
            return

        cutoff_time = datetime.utcnow() - timedelta(days=WARM_PERIOD_DAYS)
        df_stats['last_accessed'] = pd.to_datetime(df_stats['last_accessed'])
        
        active_tags = df_stats[df_stats['last_accessed'] > cutoff_time]['tag_name'].tolist()

        if not active_tags:
            print("Ticker: No active tags to warm.")
            return

        print(f"Ticker: Found {len(active_tags)} active tags.")

        # 2. Warm them (Batch of 50)
        batch_size = 50
        for i in range(0, len(active_tags), batch_size):
            batch = active_tags[i:i+batch_size]
            # Call the service DIRECTLY (Internal call)
            # Fetch last 24h to keep cache fresh
            pi_service.get_interpolated_bulk(batch, "*-24h", "*", "10m")
            print(f"Ticker: Warmed batch {i//batch_size + 1}")

        print(f"[{datetime.now()}] Ticker: Warmup Complete.")

    except Exception as e:
        print(f"Ticker Error: {e}")



#For MI Production assistace platform | VKPC
def warm_active_tags_mipa():
    """
    อุ่น (warm) cache สำหรับ `special_fetch/arrow` และ `special_fetch` โดยเน้น Tags เฉพาะ
    """
    print(f"[{datetime.now()}] Ticker-MIPA: Starting Cache Warmup for MIPA...")

    if not os.path.exists(pi_service.stats_file):
        print("Ticker-MIPA: No stats file found. Skipping.")
        return
    try:
        # 1. Find Tags ที่ถูกใช้พร้อมสำหรับ MIPA จาก CSV
        df_stats = pd.read_csv(pi_service.stats_file)
        if df_stats.empty:
            print("Ticker-MIPA: No stats yet. Skipping.")
            return

        cutoff_time = datetime.utcnow() - timedelta(days=WARM_PERIOD_DAYS)
        df_stats['last_accessed'] = pd.to_datetime(df_stats['last_accessed'])
        
        active_tags = df_stats[df_stats['last_accessed'] > cutoff_time]['tag_name'].tolist()

        if not active_tags:
            print("Ticker-MIPA: No active tags for MIPA to warm.")
            return
        print(f"Ticker-MIPA: Found {len(active_tags)} active tags.")

        # 2. Warm Tags: ใช้ค่าที่เหมาะสมกับ `special_fetch/arrow` และ `special_fetch`
        batch_size = 50
        interval = "10m"  # ระยะห่างข้อมูล
        for i in range(0, len(active_tags), batch_size):
            batch = active_tags[i:i + batch_size]

            # Fetch ข้อมูลล่าสุด 24 ชั่วโมง เพื่อรองรับ `/special_fetch/arrow` และ `/special_fetch`
            pi_service.get_interpolated_bulk(batch, "*-24h", "*", interval)
            print(f"Ticker-MIPA: Warmed batch {i // batch_size + 1} for MIPA")

        print(f"[{datetime.now()}] Ticker-MIPA: Warmup Complete for MIPA.")

    except Exception as e:
        print(f"Ticker-MIPA Error: {e}")
