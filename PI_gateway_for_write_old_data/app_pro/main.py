import asyncio
import io
import time
import pyarrow as pa
import pyarrow.feather as feather
import pandas as pd
from fastapi import FastAPI, HTTPException, Body, Response, Header, Depends
import os
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from typing import List, Optional
from app_pro.services.pi_service import pi_service
from app_pro.services.cache_warmer import warm_active_tags, warm_active_tags_mipa


app = FastAPI(title="PI Connect High-Speed Gateway")
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security Configuration
GATEWAY_TOKEN = os.getenv("GATEWAY_TOKEN", "A9r2T8#kZp2@Vxg9!QwLm4&FjN7Yc$HPs3B5eUaDS1G0oXmIQpqz0Oo8LI")

class WriteRequest(BaseModel):
    tag: str
    value: float | str | int
    timestamp: Optional[str] = None

def verify_token(authorization: str = Header(None)):
    """Simple token verification dependency."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    # Support "Bearer <token>" or just "<token>"
    token = authorization.split(" ")[-1] if " " in authorization else authorization
    
    if token != GATEWAY_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid security token")

@app.on_event("startup")
async def start_cache_ticker():
    """Runs the cache warmer every 10 minutes in the background."""
    async def ticker_loop():
        while True:
            # Run warmer in a separate thread to avoid blocking the API
            await asyncio.to_thread(warm_active_tags)
            await asyncio.sleep(600)  # Wait 10 minutes (600s)
    
    async def ticker_loop_mipa():
        while True:
            # Run warm_active_tags_mipa in a separate thread to avoid blocking
            await asyncio.to_thread(warm_active_tags_mipa)
            await asyncio.sleep(800)  #(800s)

    asyncio.create_task(ticker_loop())
    asyncio.create_task(ticker_loop_mipa())

@app.get("/ping")
def ping():
    return {"message": "pong"}

class DataRequest(BaseModel):
    tags: List[str]
    start: str = "*-7d"
    end: str = "*"
    interval: str = "1h"

@app.get("/")
def health_check():
    return {"status": "online", "server": pi_service.server_names}

@app.post("/fetch")
def fetch_data(request: DataRequest, token: str = Depends(verify_token)):
    """Standard JSON Endpoint (For Web Dashboards)"""
    t0 = time.time()
    try:
        df = pi_service.get_interpolated_bulk(
            request.tags, 
            request.start, 
            request.end, 
            request.interval
        )
        
        if df.empty:
            return {"error": "No data found", "duration_sec": time.time() - t0}

        # JSON Serialization (Slow for massive data)
        result = df.reset_index().to_dict(orient="records")
        
        return {
            "tag_count": len(df.columns),
            "row_count": len(df),
            "duration_sec": time.time() - t0,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fetch/arrow")
def fetch_data_arrow(request: DataRequest, token: str = Depends(verify_token)):
    """High-Speed Binary Endpoint (For Python Analytics)"""
    t0 = time.time()
    try:
        df = pi_service.get_interpolated_bulk(
            request.tags, 
            request.start, 
            request.end, 
            request.interval
        )
        
        if df.empty:
            return Response(content=b"", status_code=204)

        # Ensure index is a column for Arrow
        df_reset = df.reset_index().rename(columns={'index': 'Timestamp'})
        
        # SMART CLEANING: Only coerce to numeric if the column is actually numeric
        # This prevents Digital Tag strings like "RUN" from being turned into NaN
        for col in df_reset.columns:
            if col != 'Timestamp':
                # Try converting to numeric (errors become NaN)
                converted = pd.to_numeric(df_reset[col], errors='coerce')
                
                # If we still have at least one valid number, it's an Analog tag -> use cleaned numbers
                # If everything becomes NaN, it was likely a Digital tag (strings) -> keep original strings
                if converted.notna().any() or df_reset[col].isna().all():
                    df_reset[col] = converted
                else:
                    # Keep as strings for Digital tags
                    df_reset[col] = df_reset[col].astype(str)
        
        # Convert to Arrow Table
        table = pa.Table.from_pandas(df_reset)
        
        # Write to Buffer (Feather format is extremely fast)
        sink = io.BytesIO()
        feather.write_feather(table, sink, compression="uncompressed") 
        # Note: Uncompressed is often faster for local networks than burning CPU to zip
        
        return Response(content=sink.getvalue(), media_type="application/vnd.apache.arrow.file")
        
    except Exception as e:
        print(f"Arrow Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



#New gateway for MI Production assistance platform | VKPC
class DataRequest_MIPA(BaseModel):
    tags: List[str]
    start: str = "*-7d"
    end: str = "*"
    interval: str = "1h"

@app.get("/mipa/")
def health_check_mipa():
    return {"status": "online", "server": pi_service.server_names}

@app.post("/special_fetch/")
def fetch_data_mipa(request: DataRequest_MIPA, token: str = Depends(verify_token)):
    """High-Speed Metadata + Data Endpoint (Optimized & Grouped by Tag)."""
    t0 = time.time()
    
    # Retry mechanism for robust handling of connection resets
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # 1. Fetch Data (Uses L1/L2 Cache + Forced Chunking for stability)
            df = pi_service.get_interpolated_bulk(
                request.tags,
                request.start,
                request.end,
                request.interval,
                force_chunk=True
            )
            
            if df.empty:
                return {}

            # 2. Fetch Metadata (Now Cached in Redis)
            metadata_mapping = pi_service.get_tag_metadata(request.tags)

            # 3. Optimized Formatting (Grouped by Tag)
            result = {}
            # Pre-calculate timestamps with explicit UTC offset
            timestamps = [ts.strftime('%Y-%m-%dT%H:%M:%S+00:00') for ts in df.index]

            # Case-insensitive mapping for metadata and tag display
            tag_to_requested = {t.lower(): t for t in request.tags}
            metadata_by_lower = {k.lower(): v for k, v in metadata_mapping.items()}
            
            # Create a mapping of lowercase column names in df for fast lookup
            col_to_lower = {c.lower(): c for c in df.columns}

            # Optimized Formatting (Grouped by Tag) - Preserving original request order
            result = {}
            for requested_tag in request.tags:
                lower_tag = requested_tag.lower()
                if lower_tag not in col_to_lower:
                    continue
                
                tag = col_to_lower[lower_tag]
                
                # Match metadata using lowercase tag
                meta = metadata_by_lower.get(lower_tag, {})
                desc = meta.get("description", "")
                unit = meta.get("unit", "")
                
                # Convert values to list for fast C-level iteration
                values = df[tag].tolist()
                
                # Use requested case for the final result key
                display_tag = tag_to_requested.get(lower_tag, requested_tag)
                
                # Fast list comprehension (Orders of magnitude faster than df.items())
                result[display_tag] = [
                    {
                        "timestamp": ts,
                        "value": val,
                        "description": desc,
                        "unit": unit
                    }
                    for ts, val in zip(timestamps, values)
                ]

            return result

        except Exception as e:
            last_error = e
            print(f"Attempt {attempt + 1} failed for /special_fetch/: {e}")
            # If it's a ConnectionResetError, wait a bit before retrying
            if "ConnectionResetError" in str(e) or "10054" in str(e):
                time.sleep(2) # Backoff
            continue

    # If all retries fail
    print(f"All {max_retries} attempts failed for /special_fetch/: {last_error}")
    raise HTTPException(status_code=500, detail=f"All {max_retries} attempts failed: {str(last_error)}")

@app.post("/special_fetch/currentvalue")
def fetch_current_value(request: DataRequest_MIPA, token: str = Depends(verify_token)):
    """Fetch current (snapshot) values for a list of tags."""
    try:
        results = pi_service.get_current_values(request.tags)
        
        return {
            "status": "success",
            "message": "PIServer API - Current Value By Tag",
            "results": results
        }
    except Exception as e:
        print(f"Current Value Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/special_fetch/arrow/")
def fetch_data_mipa_arrow(request: DataRequest_MIPA, token: str = Depends(verify_token)):
    """High-Speed Binary Endpoint with Metadata (Optimized)."""
    t0 = time.time()
    
    # Retry mechanism
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # 1. Fetch Data (Uses L1/L2 Cache + Forced Chunking)
            df = pi_service.get_interpolated_bulk(
                request.tags,
                request.start,
                request.end,
                request.interval,
                force_chunk=True
            )
            if df.empty:
                return Response(content=b"", status_code=204)
            
            # 2. Fetch Metadata (Now Cached in Redis)
            metadata_mapping = pi_service.get_tag_metadata(request.tags)

            # 3. Formatting
            df_reset = df.reset_index().rename(columns={"index": "Timestamp"})
            for col in df.columns:
                if col in metadata_mapping:
                    meta = metadata_mapping[col]
                    df_reset[f"{col}_description"] = meta.get("description", "")
                    df_reset[f"{col}_unit"] = meta.get("unit", "")

            # Ensure column types are consistent for Arrow
            for col in df_reset.columns:
                if col != "Timestamp":
                    try:
                        df_reset[col] = pd.to_numeric(df_reset[col], errors='coerce')
                    except:
                        df_reset[col] = df_reset[col].astype(str)

            # 4. Convert to Arrow & Return
            table = pa.Table.from_pandas(df_reset)
            sink = io.BytesIO()
            feather.write_feather(table, sink, compression="uncompressed")

            return Response(
                content=sink.getvalue(),
                media_type="application/vnd.apache.arrow.file"
            )

        except Exception as e:
            last_error = e
            print(f"Attempt {attempt + 1} failed for /special_fetch/arrow/: {e}")
            if "ConnectionResetError" in str(e) or "10054" in str(e):
                time.sleep(2)
            continue

    # If all retries fail
    print(f"All {max_retries} attempts failed for /special_fetch/arrow/: {last_error}")
    raise HTTPException(status_code=500, detail=f"All {max_retries} attempts failed: {str(last_error)}")

# Add the Endpoint
@app.post("/write")
def write_tag(request: WriteRequest, token: str = Depends(verify_token)):
    """Writes a value to a PI Tag."""
    try:
        success, message = pi_service.write_tag_value(
            request.tag,
            request.value,
            request.timestamp
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return {"status": "success", "tag": request.tag, "value": request.value}
    
    except Exception as e:
        print(f"Special Arrow Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add old data to Endpoint
@app.post("/write_old")
def write_tag_old(request: WriteRequest, token: str = Depends(verify_token)):
    """Writes a value to a PI Tag."""
    try:
        success, message = pi_service.write_tag_value_old(
            request.tag,
            request.value,
            request.timestamp
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return {"status": "success", "tag": request.tag, "value": request.value}
    
    except Exception as e:
        print(f"Special Arrow Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # PRODUCTION MODE (4 Worker Processes - Max Performance)
    # uvicorn.run(app, host="0.0.0.0", port=8001, workers=4)
    uvicorn.run(app, host="0.0.0.0", port=8001)