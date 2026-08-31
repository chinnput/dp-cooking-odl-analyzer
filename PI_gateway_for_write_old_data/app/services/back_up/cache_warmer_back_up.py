import time
from datetime import datetime, timedelta
from app.services.pi_service import pi_service, TagStats
from sqlalchemy.orm import sessionmaker

# Configuration
WARM_PERIOD_DAYS = 2

def warm_active_tags():
    """
    Finds tags used in the last 2 days and refreshes their cache.
    """
    print(f"[{datetime.now()}] Ticker: Starting Cache Warmup...")
    
    if not pi_service.engine:
        print("Ticker: No DB connection. Skipping.")
        return

    try:
        # 1. Find Active Tags
        Session = sessionmaker(bind=pi_service.engine)
        session = Session()
        
        cutoff_time = datetime.utcnow() - timedelta(days=WARM_PERIOD_DAYS)
        active_tags_query = session.query(TagStats.tag_name).filter(TagStats.last_accessed > cutoff_time).all()
        active_tags = [t[0] for t in active_tags_query]
        session.close()

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
