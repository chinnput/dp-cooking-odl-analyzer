import os
import time
import pandas as pd
import redis
import json
import clr
import sys
import hashlib
from io import StringIO
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# --- PostgreSQL Setup ---
Base = declarative_base()

class DataCache(Base):
    __tablename__ = 'pi_data_cache'
    key = Column(String, primary_key=True)
    data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class TagStats(Base):
    __tablename__ = 'tag_stats'
    tag_name = Column(String, primary_key=True)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    hit_count = Column(Integer, default=1)

class TagRoute(Base):
    __tablename__ = 'tag_routes'
    tag_name = Column(String, primary_key=True)
    server_name = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

# Initialize AFSDK
sys.path.append(r'C:\Program Files (x86)\PIPC\AF\PublicAssemblies\4.0')
clr.AddReference('OSIsoft.AFSDK')
from OSIsoft.AF.PI import PIServers, PIPoint, PIPointList, PIPagingConfiguration, PIPageType
from OSIsoft.AF.Time import AFTime, AFTimeRange, AFTimeSpan
from System import String, Boolean
from System.Collections.Generic import List

class PIGatewayService:
    def __init__(self):
        self.server_names = [s.strip() for s in os.getenv("PI_SERVERS", "SKIC-PISERVER").split(",")]
        self.mock_mode = os.getenv("MOCK_MODE", "False").lower() == "true"
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6381)),
            decode_responses=True
        )
        self._init_postgres()
        self.pi_servers = self._connect_pi_servers()

    def _init_postgres(self):
        try:
            db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
            self.engine = create_engine(db_url)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            print("PostgreSQL L2 Cache Initialized.")
        except Exception as e:
            print(f"PostgreSQL Initialization Error: {e}")
            self.engine = None

    def _connect_pi_servers(self):
        """Connects to all configured PI Servers."""
        server_conns = {}
        failed_servers = []
        
        if self.mock_mode:
            print("WARNING: Running in MOCK MODE.")
            return {}

        print("--- Connecting to PI Servers ---")
        pi_servers = PIServers()
        for name in self.server_names:
            try:
                server = pi_servers[name]
                if not server.ConnectionInfo.IsConnected:
                    server.Connect(False)
                server_conns[name] = server
                print(f"✅ Connected: {name}")
            except Exception as e:
                failed_servers.append(name)
                # print(f"❌ Failed: {name} ({e})") # Optional: Uncomment for full verbose error

        print("-" * 30)
        print(f"Gateway Ready with {len(server_conns)} Active Servers: {list(server_conns.keys())}")
        if failed_servers:
            print(f"⚠️  Ignored {len(failed_servers)} Unreachable Servers: {failed_servers}")
        print("-" * 30)
        
        return server_conns

    def _snap_time(self, dt_obj, interval):
        """Aligns time to the nearest interval boundary for better caching."""
        try:
            if 'm' in interval:
                minutes = int(interval.replace('m', ''))
                snapped_min = (dt_obj.minute // minutes) * minutes
                return dt_obj.replace(minute=snapped_min, second=0, microsecond=0)
            elif 'h' in interval:
                return dt_obj.replace(minute=0, second=0, microsecond=0)
            elif 'd' in interval:
                return dt_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        except:
            return dt_obj.replace(second=0, microsecond=0)
        return dt_obj

    def get_interpolated_bulk(self, tags, start_str, end_str, interval):
        """
        Smart Per-Tag Caching Implementation with Time Snapping.
        """
        # 0. Track Usage
        self._track_usage(tags)

        # 1. Parse Times
        try:
            if end_str == "*":
                end_dt = datetime.now()
            else:
                end_dt = pd.to_datetime(end_str) if not self.mock_mode else datetime.now()

            if "*-" in start_str:
                unit = start_str[-1]
                val = int(start_str[2:-1])
                if unit == 'd': delta = timedelta(days=val)
                elif unit == 'h': delta = timedelta(hours=val)
                elif unit == 'm': delta = timedelta(minutes=val)
                else: delta = timedelta(hours=24)
                start_dt = end_dt - delta
            else:
                start_dt = pd.to_datetime(start_str)

            # 2. SNAP Times
            start_dt = self._snap_time(start_dt, interval)
            end_dt = self._snap_time(end_dt, interval)

            cache_start = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            cache_end = end_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Time Parsing Error: {e}")
            cache_start = start_str
            cache_end = end_str

        # 3. Generate Keys
        tag_keys = {tag: f"pi_data:{tag}:{cache_start}:{cache_end}:{interval}" for tag in tags}
        all_keys = list(tag_keys.values())
        
        found_data = {} 
        missing_tags = []

        # 4. Check L1 (Redis)
        try:
            redis_results = self.redis_client.mget(all_keys)
            for tag, val in zip(tags, redis_results):
                if val:
                    found_data[tag] = pd.read_json(StringIO(val), typ='series')
                else:
                    missing_tags.append(tag)
        except Exception as e:
            print(f"Redis Error: {e}")
            missing_tags = list(tags) 

        # 5. Check L2 (Postgres)
        tags_still_missing = []
        if missing_tags and self.engine:
            try:
                missing_keys = [tag_keys[t] for t in missing_tags]
                session = self.Session()
                results = session.query(DataCache).filter(DataCache.key.in_(missing_keys)).all()
                db_hits = {row.key: row.data for row in results}
                
                for tag in missing_tags:
                    key = tag_keys[tag]
                    if key in db_hits:
                        s = pd.read_json(StringIO(db_hits[key]), typ='series')
                        found_data[tag] = s
                        self.redis_client.setex(key, int(os.getenv("CACHE_TTL_DATA", 300)), db_hits[key])
                    else:
                        tags_still_missing.append(tag)
                session.close()
            except Exception as e:
                print(f"Postgres Error: {e}")
                tags_still_missing = missing_tags
        else:
            tags_still_missing = missing_tags

        # 6. Cold Fetch (Smart Server Routing)
        if tags_still_missing:
            cold_df = self._perform_cold_fetch(tags_still_missing, cache_start, cache_end, interval, cache_start, cache_end)
            if not cold_df.empty:
                for col in cold_df.columns:
                    found_data[col] = cold_df[col]

        # 7. Merge & Return
        if not found_data:
            return pd.DataFrame()

        final_df = pd.DataFrame(found_data)
        final_df.index = pd.to_datetime(final_df.index)
        final_df.sort_index(inplace=True)
        return final_df

    def _resolve_tag_routes(self, tags):
        """Maps tags to servers using DB lookup + Auto-Discovery."""
        routing = {} # {server_name: [tags]}
        tag_to_server = {} # {tag: server_name}
        missing_discovery = []

        if not self.engine:
            default_server = self.server_names[0]
            return {default_server: list(tags)}

        # 1. DB Lookup
        try:
            session = self.Session()
            results = session.query(TagRoute).filter(TagRoute.tag_name.in_(tags)).all()
            for row in results:
                tag_to_server[row.tag_name] = row.server_name
            session.close()
        except: pass

        for t in tags:
            if t not in tag_to_server: missing_discovery.append(t)

        # 2. Discovery
        if missing_discovery:
            print(f"DISCOVERY: Searching for {len(missing_discovery)} tags...")
            for tag in missing_discovery:
                found_server = None
                for s_name, s_conn in self.pi_servers.items():
                    try:
                        if PIPoint.FindPIPoint(s_conn, tag):
                            found_server = s_name
                            break
                    except: continue
                
                if found_server:
                    tag_to_server[tag] = found_server
                    try:
                        session = self.Session()
                        session.add(TagRoute(tag_name=tag, server_name=found_server))
                        session.commit()
                        session.close()
                    except: pass

        # 3. Grouping
        for tag, s_name in tag_to_server.items():
            if s_name not in routing: routing[s_name] = []
            routing[s_name].append(tag)
        
        return routing

    def _perform_cold_fetch(self, tags, start_str, end_str, interval, cache_start, cache_end):
        """Routes tags to correct servers and fetches data."""
        server_groups = self._resolve_tag_routes(tags)
        all_results_df = pd.DataFrame()

        for s_name, s_tags in server_groups.items():
            s_conn = self.pi_servers.get(s_name)
            if not s_conn: continue
            
            try:
                af_start = AFTime(start_str).LocalTime
                af_end = AFTime(end_str).LocalTime
                py_start = datetime(af_start.Year, af_start.Month, af_start.Day, af_start.Hour, af_start.Minute, af_start.Second)
                py_end = datetime(af_end.Year, af_end.Month, af_end.Day, af_end.Hour, af_end.Minute, af_end.Second)
                duration_days = (py_end - py_start).days
                is_high_freq = "m" in interval or "s" in interval
                
                if duration_days > 15 and is_high_freq:
                    df = self._fetch_chunked(s_tags, s_conn, py_start, py_end, interval)
                else:
                    df = self._fetch_standard(s_tags, s_conn, start_str, end_str, interval)
                
                if not df.empty:
                    for tag in df.columns:
                        series = df[tag]
                        key = f"pi_data:{tag}:{cache_start}:{cache_end}:{interval}"
                        self._save_single_tag(key, series)
                    
                    if all_results_df.empty: all_results_df = df
                    else: all_results_df = all_results_df.join(df, how='outer')
            except Exception as e:
                print(f"Error fetching from {s_name}: {e}")

        return all_results_df

    def _track_usage(self, tags):
        if not self.engine: return
        try:
            session = self.Session()
            for tag in tags:
                stat = session.query(TagStats).filter_by(tag_name=tag).first()
                if stat:
                    stat.last_accessed = datetime.utcnow()
                    stat.hit_count += 1
                else:
                    session.add(TagStats(tag_name=tag))
            session.commit()
            session.close()
        except Exception as e:
            print(f"Stats Tracking Error: {e}")

    def _save_single_tag(self, key, series):
        # Ensure unique index before JSON conversion
        if not series.index.is_unique:
            series = series[~series.index.duplicated(keep='first')]
            
        json_data = series.to_json()
        try: self.redis_client.setex(key, int(os.getenv("CACHE_TTL_DATA", 300)), json_data)
        except: pass

        if self.engine:
            try:
                session = self.Session()
                cache_entry = session.query(DataCache).filter_by(key=key).first()
                if cache_entry:
                    cache_entry.data = json_data
                    cache_entry.created_at = datetime.utcnow()
                else:
                    session.add(DataCache(key=key, data=json_data))
                session.commit()
                session.close()
            except: pass

    def _fetch_standard(self, tags, s_conn, start, end, interval):
        point_list = self._resolve_tags_bulk(tags, s_conn)
        if point_list.Count == 0: return pd.DataFrame()
        def to_af_time(t):
            if isinstance(t, datetime): return AFTime(t.strftime("%Y-%m-%d %H:%M:%S"))
            return AFTime(str(t))
        time_range = AFTimeRange(to_af_time(start), to_af_time(end))
        span = AFTimeSpan.Parse(interval)
        paging_config = PIPagingConfiguration(PIPageType.TagCount, 100)
        bulk_results = point_list.InterpolatedValues(time_range, span, None, False, paging_config)
        return self._results_to_df(bulk_results)

    def _fetch_chunked(self, tags, s_conn, start_dt, end_dt, interval):
        chunk_days = 15
        current_start = start_dt
        all_dfs = []
        point_list = self._resolve_tags_bulk(tags, s_conn)
        span = AFTimeSpan.Parse(interval)
        paging_config = PIPagingConfiguration(PIPageType.TagCount, 100)
        while current_start < end_dt:
            current_end = min(current_start + timedelta(days=chunk_days), end_dt)
            time_range = AFTimeRange(AFTime(current_start.strftime("%Y-%m-%d %H:%M:%S")), AFTime(current_end.strftime("%Y-%m-%d %H:%M:%S")))
            try:
                bulk_results = point_list.InterpolatedValues(time_range, span, None, False, paging_config)
                chunk_df = self._results_to_df(bulk_results)
                if not chunk_df.empty: all_dfs.append(chunk_df)
            except: pass
            current_start = current_end
        if not all_dfs: return pd.DataFrame()
        final_df = pd.concat(all_dfs)
        return final_df[~final_df.index.duplicated(keep='first')]

    def _results_to_df(self, bulk_results):
        data_dict = {}
        for result in bulk_results:
            tag_name = result.PIPoint.Name
            values = []
            timestamps = []
            for val in result:
                v = val.Value
                if hasattr(v, "Name"): v = v.Name
                elif not isinstance(v, (int, float, str, type(None))): v = str(v)
                values.append(v)
                timestamps.append(val.Timestamp.LocalTime.ToString("yyyy-MM-dd HH:mm:ss"))
            data_dict[tag_name] = pd.Series(values, index=timestamps)
        return pd.DataFrame(data_dict)

    def _resolve_tags_bulk(self, tag_names, s_conn):
        point_list = PIPointList()
        csharp_tag_list = List[String]()
        for t in tag_names: csharp_tag_list.Add(t)
        found_points = PIPoint.FindPIPoints(s_conn, csharp_tag_list, None)
        for pt in found_points:
            point_list.Add(pt)
            self.redis_client.setex(f"pi_tag:{pt.Name}", int(os.getenv("CACHE_TTL_TAGS", 86400)), str(pt.ID))
        return point_list

pi_service = PIGatewayService()
