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

load_dotenv()

# Initialize AFSDK
sys.path.append(r'C:\Program Files (x86)\PIPC\AF\PublicAssemblies\4.0')
clr.AddReference('OSIsoft.AFSDK')
from OSIsoft.AF.PI import PIServers, PIPoint, PIPointList, PIPagingConfiguration, PIPageType
from OSIsoft.AF.Time import AFTime, AFTimeRange, AFTimeSpan
from System import String, Boolean, Object, DateTime as SysDateTime, DateTimeKind
from System.Collections.Generic import List
# Add more function
from OSIsoft.AF.Asset import AFValue
from OSIsoft.AF.Data import AFUpdateOption


class PIGatewayService:
    def __init__(self):
        self.server_names = [s.strip() for s in os.getenv("PI_SERVERS", "VPKGDRBPPI01").split(",")]
        self.mock_mode = os.getenv("MOCK_MODE", "False").lower() == "true"
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6381)),
            decode_responses=True
        )
        
        # --- CSV Storage Setup ---
        self.storage_dir = os.path.join("app_pro", "storage")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.cache_file = os.path.join(self.storage_dir, "pi_data_cache.csv")
        self.stats_file = os.path.join(self.storage_dir, "tag_stats.csv")
        self.routes_file = os.path.join(self.storage_dir, "tag_routes.csv")
        self._init_csv_storage()
        
        self.pi_servers = self._connect_pi_servers()

    def _init_csv_storage(self):
        """Initializes CSV files if they don't exist."""
        try:
            if not os.path.exists(self.cache_file):
                pd.DataFrame(columns=["key", "data", "created_at"]).to_csv(self.cache_file, index=False)
            if not os.path.exists(self.stats_file):
                pd.DataFrame(columns=["tag_name", "last_accessed", "hit_count"]).to_csv(self.stats_file, index=False)
            if not os.path.exists(self.routes_file):
                pd.DataFrame(columns=["tag_name", "server_name", "last_updated"]).to_csv(self.routes_file, index=False)
            print("CSV L2 Cache Initialized.")
        except Exception as e:
            print(f"CSV Initialization Error: {e}")

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

    def get_interpolated_bulk(self, tags, start_str, end_str, interval, force_chunk=False):
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

        # 5. Check L2 (CSV)
        tags_still_missing = []
        if missing_tags:
            try:
                df_cache = pd.read_csv(self.cache_file, on_bad_lines='skip')
                missing_keys = [tag_keys[t] for t in missing_tags]
                db_hits = df_cache[df_cache['key'].isin(missing_keys)]
                hits_dict = dict(zip(db_hits['key'], db_hits['data']))
                
                for tag in missing_tags:
                    key = tag_keys[tag]
                    if key in hits_dict:
                        data_str = hits_dict[key]
                        s = pd.read_json(StringIO(data_str), typ='series')
                        found_data[tag] = s
                        self.redis_client.setex(key, int(os.getenv("CACHE_TTL_DATA", 300)), data_str)
                    else:
                        tags_still_missing.append(tag)
            except Exception as e:
                print(f"CSV L2 Read Error: {e}")
                tags_still_missing = missing_tags
        else:
            tags_still_missing = missing_tags

        # 6. Cold Fetch (Smart Server Routing)
        if tags_still_missing:
            cold_df = self._perform_cold_fetch(tags_still_missing, start_dt, end_dt, interval, cache_start, cache_end, force_chunk=force_chunk)
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
        """Maps tags to servers using CSV lookup + Auto-Discovery."""
        routing = {} # {server_name: [tags]}
        tag_to_server = {} # {tag: server_name}
        missing_discovery = []

        # 1. CSV Lookup
        try:
            df_routes = pd.read_csv(self.routes_file, on_bad_lines='skip')
            route_hits = df_routes[df_routes['tag_name'].isin(tags)]
            tag_to_server = dict(zip(route_hits['tag_name'], route_hits['server_name']))
        except Exception as e:
            print(f"CSV Routes Read Error: {e}")

        for t in tags:
            if t not in tag_to_server: missing_discovery.append(t)

        # 2. Discovery
        if missing_discovery:
            print(f"DISCOVERY: Searching for {len(missing_discovery)} tags...")
            new_routes = []
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
                    new_routes.append({"tag_name": tag, "server_name": found_server, "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})

            if new_routes:
                try:
                    df_routes = pd.read_csv(self.routes_file, on_bad_lines='skip')
                    df_new = pd.DataFrame(new_routes)
                    df_routes = pd.concat([df_routes[~df_routes['tag_name'].isin(df_new['tag_name'])], df_new], ignore_index=True)
                    df_routes.to_csv(self.routes_file, index=False)
                except Exception as e:
                    print(f"CSV Routes Write Error: {e}")

        # 3. Grouping
        for tag, s_name in tag_to_server.items():
            if s_name not in routing: routing[s_name] = []
            routing[s_name].append(tag)
        
        return routing

    def _perform_cold_fetch(self, tags, start_dt, end_dt, interval, cache_start, cache_end, force_chunk=False):
        """Routes tags to correct servers and fetches data."""
        server_groups = self._resolve_tag_routes(tags)
        all_results_df = pd.DataFrame()

        for s_name, s_tags in server_groups.items():
            s_conn = self.pi_servers.get(s_name)
            if not s_conn: continue
            
            try:
                py_start = start_dt
                py_end = end_dt
                duration_days = (py_end - py_start).days
                is_high_freq = "m" in interval or "s" in interval
                
                if force_chunk or (duration_days > 15 and is_high_freq) or (duration_days > 30):
                    df = self._fetch_chunked(s_tags, s_conn, py_start, py_end, interval)
                else:
                    df = self._fetch_standard(s_tags, s_conn, py_start, py_end, interval)
                
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
        try:
            try:
                df_stats = pd.read_csv(self.stats_file, on_bad_lines='skip')
            except:
                df_stats = pd.DataFrame(columns=["tag_name", "last_accessed", "hit_count"])

            now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            for tag in tags:
                if not df_stats.empty and tag in df_stats['tag_name'].values:
                    df_stats.loc[df_stats['tag_name'] == tag, 'last_accessed'] = now_str
                    df_stats.loc[df_stats['tag_name'] == tag, 'hit_count'] += 1
                else:
                    new_row = pd.DataFrame([{"tag_name": tag, "last_accessed": now_str, "hit_count": 1}])
                    df_stats = pd.concat([df_stats, new_row], ignore_index=True)
            
            df_stats.to_csv(self.stats_file, index=False)
        except Exception as e:
            print(f"Stats Tracking Error: {e}")

    def _save_single_tag(self, key, series):
        # Ensure unique index before JSON conversion
        if not series.index.is_unique:
            series = series[~series.index.duplicated(keep='first')]
            
        json_data = series.to_json()
        try: self.redis_client.setex(key, int(os.getenv("CACHE_TTL_DATA", 300)), json_data)
        except: pass

        try:
            try:
                df_cache = pd.read_csv(self.cache_file, on_bad_lines='skip')
            except:
                # If file is totally corrupted, start fresh
                df_cache = pd.DataFrame(columns=["key", "data", "created_at"])

            now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            if not df_cache.empty and key in df_cache['key'].values:
                df_cache.loc[df_cache['key'] == key, 'data'] = json_data
                df_cache.loc[df_cache['key'] == key, 'created_at'] = now_str
            else:
                new_row = pd.DataFrame([{"key": key, "data": json_data, "created_at": now_str}])
                df_cache = pd.concat([df_cache, new_row], ignore_index=True)
            
            df_cache.to_csv(self.cache_file, index=False)
        except Exception as e:
            print(f"CSV Cache Write Error: {e}")

    def _fetch_standard(self, tags, s_conn, start, end, interval):
        point_list = self._resolve_tags_bulk(tags, s_conn)
        if point_list.Count == 0: return pd.DataFrame()
        def to_af_time(t):
            if isinstance(t, datetime):
                return AFTime(SysDateTime(t.year, t.month, t.day, t.hour, t.minute, t.second, DateTimeKind.Local))
            return AFTime(str(t))
        time_range = AFTimeRange(to_af_time(start), to_af_time(end))
        span = AFTimeSpan.Parse(interval)
        paging_config = PIPagingConfiguration(PIPageType.TagCount, 100)
        bulk_results = point_list.InterpolatedValues(time_range, span, None, False, paging_config)
        return self._results_to_df(bulk_results)

    def _fetch_chunked(self, tags, s_conn, start_dt, end_dt, interval):
        if "h" in interval:
            chunk_days = 60
        elif "m" in interval or "s" in interval:
            chunk_days = 15
        else:
            chunk_days = 30
            
        current_start = start_dt
        all_dfs = []
        point_list = self._resolve_tags_bulk(tags, s_conn)
        span = AFTimeSpan.Parse(interval)
        paging_config = PIPagingConfiguration(PIPageType.TagCount, 100)
        
        def to_af_time(t):
            return AFTime(SysDateTime(t.year, t.month, t.day, t.hour, t.minute, t.second, DateTimeKind.Local))
            
        while current_start < end_dt:
            current_end = min(current_start + timedelta(days=chunk_days), end_dt)
            time_range = AFTimeRange(to_af_time(current_start), to_af_time(current_end))
            try:
                bulk_results = point_list.InterpolatedValues(time_range, span, None, False, paging_config)
                chunk_df = self._results_to_df(bulk_results)
                if not chunk_df.empty: all_dfs.append(chunk_df)
            except Exception as e:
                print(f"Error in _fetch_chunked chunk: {e}")
                
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
                lt = val.Timestamp.LocalTime
                timestamps.append(f"{lt.Year:04d}-{lt.Month:02d}-{lt.Day:02d} {lt.Hour:02d}:{lt.Minute:02d}:{lt.Second:02d}")
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

    def get_tag_metadata(self, tags):
        """Fetches tag metadata (description, units) with Redis caching."""
        metadata = {}
        missing_tags = []

        for tag in tags:
            cache_key = f"pi_meta:{tag}"
            try:
                cached_val = self.redis_client.get(cache_key)
                if cached_val:
                    metadata[tag] = json.loads(cached_val)
                else:
                    missing_tags.append(tag)
            except:
                missing_tags.append(tag)

        if not missing_tags:
            return metadata

        for tag in missing_tags:
            found = False
            for server_name, server_conn in self.pi_servers.items():
                try:
                    pi_point = PIPoint.FindPIPoint(server_conn, tag)
                    if pi_point:
                        attributes = pi_point.GetAttributes(["descriptor", "engunits"])
                        attributes_dict = {}
                        for key in attributes.Keys:
                            attributes_dict[key] = attributes[key]
                        
                        description = str(attributes_dict.get("descriptor", "No description available"))
                        unit = str(attributes_dict.get("engunits", "No engunit attribute"))
                        
                        meta_val = {
                            "description": description,
                            "unit": unit,
                        }
                        metadata[tag] = meta_val
                        
                        try:
                            self.redis_client.setex(f"pi_meta:{tag}", 86400, json.dumps(meta_val))
                        except:
                            pass
                        found = True
                        break
                except Exception:
                    continue
            
            if not found:
                metadata[tag] = {
                    "description": "No description available",
                    "unit": "No unit provided",
                }

        return metadata

    def get_current_values(self, tags):
        """Fetches the latest (snapshot) values for a list of tags."""
        results = {}
        if self.mock_mode:
            return {tag: 20.61 for tag in tags}

        server_groups = self._resolve_tag_routes(tags)
        
        for s_name, s_tags in server_groups.items():
            s_conn = self.pi_servers.get(s_name)
            if not s_conn: continue
            
            try:
                point_list = self._resolve_tags_bulk(s_tags, s_conn)
                for pt in point_list:
                    try:
                        snap = pt.Snapshot()
                        val = snap.Value
                        if hasattr(val, "Name"):
                            val = str(val.Name)
                        elif not isinstance(val, (int, float, str, type(None))):
                            val = str(val)
                        
                        results[pt.Name] = val
                    except Exception as pt_e:
                        print(f"Error fetching snapshot for {pt.Name}: {pt_e}")
            except Exception as e:
                print(f"Error fetching snapshots from {s_name}: {e}")
        
        return results

    def write_tag_value(self, tag, value, timestamp=None):
        """Writes a single value to a PI Tag."""
        if self.mock_mode:
            print(f"MOCK: Writing {value} to {tag}")
            return True, "Mock success"

        try:
            routing = self._resolve_tag_routes([tag])
            if not routing:
                return False, f"Tag {tag} not found on any configured server."
            
            server_name = list(routing.keys())[0]
            server_conn = self.pi_servers.get(server_name)
            
            if not server_conn:
                return False, f"Server {server_name} is not connected."

            pi_point = PIPoint.FindPIPoint(server_conn, tag)
            af_time = AFTime(timestamp) if timestamp else AFTime.Now
            
            try:
                numeric_val = float(value)
                af_value = AFValue(numeric_val, af_time)
            except (ValueError, TypeError):
                af_value = AFValue(String(str(value)), af_time)

            pi_point.UpdateValue(af_value, AFUpdateOption.Replace)
            self._track_usage([tag])
            
            return True, "Success"
            
        except Exception as e:
            return False, str(e)


    #Update PI-tag data for old data

    def _parse_af_time(self, timestamp):
        """
        Parse timestamp as explicit UTC+07:00 time to avoid machine timezone issues.
        Input examples:
        - 2026-07-31 18:00:00
        - 2026-07-31T18:00:00
        - 31/07/2026 18:00:00
        """
        if timestamp is None:
            raise ValueError("timestamp is required")

        if not isinstance(timestamp, str):
            raise ValueError("timestamp must be a string")

        ts = timestamp.strip()

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(ts, fmt)

                # Explicit timezone offset to prevent implicit conversion
                normalized = dt.strftime("%m/%d/%Y %H:%M:%S") + " +07:00"

                return AFTime(normalized)
            except ValueError:
                continue

        raise ValueError(
            "Invalid timestamp format. Example: '2026-07-31 18:00:00'"
        )


    def write_tag_value_old(self, tag, value, timestamp):
        """Writes a single value to a PI Tag with specified timestamp."""
        if self.mock_mode:
            print(f"MOCK: Writing {value} to {tag} at {timestamp}")
            return True, "Mock success"

        try:
            routing = self._resolve_tag_routes([tag])
            if not routing:
                return False, f"Tag {tag} not found on any configured server."
            
            server_name = list(routing.keys())[0]
            server_conn = self.pi_servers.get(server_name)
            
            if not server_conn:
                return False, f"Server {server_name} is not connected."

            pi_point = PIPoint.FindPIPoint(server_conn, tag)
            af_time = self._parse_af_time(timestamp)

            try:
                numeric_val = float(value)
                af_value = AFValue(numeric_val, af_time)
            except (ValueError, TypeError):
                af_value = AFValue(String(str(value)), af_time)

            pi_point.UpdateValue(af_value, AFUpdateOption.Replace)

            self._track_usage([tag])
            return True, f"Success: wrote value at {timestamp}"

        except ValueError as e:
            return False, str(e)
        except Exception:
            return False, "Something went wrong, but I can help you try again."


    def cleanup_old_csv_cache(self, days=7):
        """Removes records older than specified days from the CSV cache."""
        try:
            if not os.path.exists(self.cache_file):
                return

            df_cache = pd.read_csv(self.cache_file, on_bad_lines='skip')
            if df_cache.empty or 'created_at' not in df_cache.columns:
                return

            cutoff_time = datetime.utcnow() - timedelta(days=days)
            df_cache['created_at_dt'] = pd.to_datetime(df_cache['created_at'], errors='coerce')
            
            original_count = len(df_cache)
            df_cache = df_cache[df_cache['created_at_dt'] >= cutoff_time]
            df_cache = df_cache.drop(columns=['created_at_dt'])
            
            if len(df_cache) < original_count:
                df_cache.to_csv(self.cache_file, index=False)
                print(f"CSV Cleanup: Removed {original_count - len(df_cache)} old cache records (older than {days} days).")
        except Exception as e:
            print(f"CSV Cleanup Error: {e}")

pi_service = PIGatewayService()
