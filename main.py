"""
main.py — FastAPI layer for Vital 2.0 AQI Forecasting System

Runs on EC2-B (Elastic IP 32.196.37.69).
Orchestrates Stages 1-10, syncs with S3, uploads outputs.
"""

import os
import sys
import json
import math
import logging
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# ============================================================
# Environment
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parent
ENV_FILE = BACKEND_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================
# Paths
# ============================================================

DATA_DIR = BACKEND_DIR / "data"
OUTPUTS_DIR = BACKEND_DIR / "outputs"
LOGS_DIR = BACKEND_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
STAGE_DIRS = {f"stage{i}": BACKEND_DIR / f"stage{i}" for i in range(1, 11)}

# ============================================================
# S3 upload map
# ============================================================

S3_UPLOAD_MAP = [
    ("regional_forecast.csv",         "aqi-forecast",   "forecasts/regional_forecast.csv"),
    ("spatial_model_results.csv",     "aqi-forecast",   "spatial/spatial_model_results.csv"),
    ("validation_metrics.csv",        "aqi-validation", "validation/metrics.csv"),
    ("biomass_fire_emissions.csv",    "aqi-raw",        "fires/biomass_fire_emissions.csv"),
    ("spatial_emission_inventory.csv","aqi-processed",  "emissions/inventory.csv"),
    ("chemistry_summary.csv",         "aqi-wrfchem",    "chemistry/summary.csv"),
    ("feedback_summary.csv",          "aqi-wrfchem",    "feedback/summary.csv"),
    ("live_raw.json",                 "aqi-raw",        "live/latest.json"),
]

# ============================================================
# AWS
# ============================================================

try:
    import boto3
    import pandas as pd
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    logger.info(f"✅ AWS clients initialized (region={AWS_REGION})")
except Exception as e:
    logger.warning(f"⚠️ AWS unavailable: {e}")
    s3_client = None
    dynamodb = None
    AWS_REGION = "us-east-1"
    try:
        import pandas as pd
    except ImportError:
        pd = None

# ============================================================
# Redis
# ============================================================

try:
    import redis
    REDIS_HOST = os.getenv("REDIS_HOST", "").strip()
    if REDIS_HOST:
        redis_client = redis.Redis(
            host=REDIS_HOST, port=6379, decode_responses=True,
            socket_connect_timeout=2,
        )
        redis_client.ping()
        logger.info(f"✅ Redis connected: {REDIS_HOST}")
    else:
        redis_client = None
        logger.info("ℹ️ Redis not configured")
except Exception as e:
    logger.warning(f"⚠️ Redis unavailable: {e}")
    redis_client = None

# ============================================================
# App
# ============================================================

app = FastAPI(
    title="Vital 2.0 — Delhi NCR AQI Forecasting API",
    version="2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Helpers
# ============================================================

def find_latest_file(directory, patterns):
    if not isinstance(patterns, (list, tuple)):
        patterns = [patterns]
    candidates = []
    for pattern in patterns:
        candidates.extend(directory.glob(pattern))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_csv_safe(path):
    if path is None or not Path(path).exists() or pd is None:
        return None
    try:
        return pd.read_csv(path)
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return None


def pm25_to_aqi(pm25):
    if pm25 <= 12.0:
        return round((50 / 12.0) * pm25)
    if pm25 <= 35.4:
        return round(((100 - 51) / (35.4 - 12.1)) * (pm25 - 12.1) + 51)
    if pm25 <= 55.4:
        return round(((150 - 101) / (55.4 - 35.5)) * (pm25 - 35.5) + 101)
    if pm25 <= 150.4:
        return round(((200 - 151) / (150.4 - 55.5)) * (pm25 - 55.5) + 151)
    if pm25 <= 250.4:
        return round(((300 - 201) / (250.4 - 150.5)) * (pm25 - 150.5) + 201)
    return round(((500 - 301) / (500.4 - 250.5)) * (pm25 - 250.5) + 301)


def aqi_category(aqi):
    if aqi <= 50:
        return {"category": "Good", "color": "#00e400", "risk": "Low"}
    if aqi <= 100:
        return {"category": "Moderate", "color": "#ffff00", "risk": "Moderate"}
    if aqi <= 150:
        return {"category": "Unhealthy for Sensitive", "color": "#ff7e00", "risk": "Sensitive"}
    if aqi <= 200:
        return {"category": "Unhealthy", "color": "#ff0000", "risk": "Unhealthy"}
    if aqi <= 300:
        return {"category": "Very Unhealthy", "color": "#8f3f97", "risk": "Very Unhealthy"}
    return {"category": "Hazardous", "color": "#7e0023", "risk": "Hazardous"}


def _safe_float(v):
    try:
        if v is None:
            return None
        f = float(v)
        if math.isnan(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _extract_station_values(latest):
    """Extract all fields from a CSV row. Returns dict with None for missing."""
    u = _safe_float(latest.get("u_wind_m_s"))
    v = _safe_float(latest.get("v_wind_m_s"))
    wind_speed = _safe_float(latest.get("wind_speed_m_s"))
    wind_dir = _safe_float(latest.get("wind_direction_deg"))

    if wind_speed is None and u is not None and v is not None:
        wind_speed = math.sqrt(u * u + v * v)
    if wind_dir is None and u is not None and v is not None:
        wind_dir = (math.degrees(math.atan2(-u, -v)) + 360) % 360

    pm25 = _safe_float(latest.get("PM25")) or 0.0
    aqi = pm25_to_aqi(pm25)
    cat = aqi_category(aqi)

    return {
        "aqi": aqi,
        "aqi_category": cat["category"],
        "color": cat["color"],
        "risk": cat["risk"],
        "pm25": round(pm25, 2),
        "pm10": round(_safe_float(latest.get("PM10")) or 0.0, 2),
        "no2": round(_safe_float(latest.get("NO2")) or 0.0, 2),
        "o3": round(_safe_float(latest.get("O3")) or 0.0, 2),
        "co": round(_safe_float(latest.get("CO")) or 0.0, 3),
        "temperature_C": _safe_float(latest.get("temperature_C")),
        "humidity": _safe_float(latest.get("humidity")),
        "pbl_height_m": _safe_float(latest.get("PBLH_m")),
        "wind_speed": round(wind_speed, 2) if wind_speed is not None else None,
        "wind_direction": round(wind_dir, 1) if wind_dir is not None else None,
        "radiation_W_m2": _safe_float(latest.get("radiation_W_m2")),
    }


# ============================================================
# Root + Health + Stages
# ============================================================

@app.get("/")
def root():
    return {
        "service": "Vital 2.0 AQI Forecasting API",
        "version": "2.0",
        "status": "running",
        "time": datetime.utcnow().isoformat() + "Z",
        "endpoints": {
            "health":          "/api/health",
            "stages":          "/api/stages",
            "predict":         "/api/predict",
            "predict_batch":   "/api/predict/batch",
            "live":            "/api/live",
            "live_batch":      "/api/live/batch",
            "forecast_24h":    "/api/forecast/24h",
            "forecast_48h":    "/api/forecast/48h",
            "forecast_72h":    "/api/forecast/72h",
            "heatmap":         "/api/heatmap",
            "validation":      "/api/validation",
            "fires":           "/api/fires",
            "emissions":       "/api/emissions",
            "s3_status":       "/api/s3-status",
            "run_pipeline":    "/api/run-pipeline (POST)",
            "run_forecast":    "/api/run-forecast (POST)",
            "run_stage":       "/api/run-stage/{stage} (POST)",
            "upload_outputs":  "/api/upload-outputs (POST)",
            "sync_from_s3":    "/api/sync-from-s3 (POST)",
        },
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat() + "Z",
        "services": {
            "s3": s3_client is not None,
            "dynamodb": dynamodb is not None,
            "redis": redis_client is not None,
            "aws_region": AWS_REGION,
        },
        "paths": {
            "backend": str(BACKEND_DIR),
            "data": str(DATA_DIR),
            "outputs": str(OUTPUTS_DIR),
        },
    }


@app.get("/api/stages")
def list_stages():
    result = {}
    for stage_name, stage_path in STAGE_DIRS.items():
        if stage_path.exists():
            files = [f.name for f in stage_path.iterdir() if f.is_file()]
            dirs = [d.name for d in stage_path.iterdir() if d.is_dir()]
            result[stage_name] = {"exists": True, "files": files[:20], "subdirs": dirs[:10]}
        else:
            result[stage_name] = {"exists": False}
    return {
        "stages": result,
        "outputs": sorted([f.name for f in OUTPUTS_DIR.iterdir()]) if OUTPUTS_DIR.exists() else [],
        "data": sorted([f.name for f in DATA_DIR.iterdir()]) if DATA_DIR.exists() else [],
    }


# ============================================================
# /api/predict — single location (from CSV)
# ============================================================

@app.get("/api/predict")
def predict(lat: float = Query(28.6139), lng: float = Query(77.2090)):
    cache_key = f"predict:{lat}:{lng}"
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    forecast_file = find_latest_file(OUTPUTS_DIR, ["regional_forecast*.csv", "forecast*.csv"])
    forecast_df = load_csv_safe(forecast_file)

    if forecast_df is None or forecast_df.empty:
        raise HTTPException(
            status_code=503,
            detail="No forecast output. POST /api/run-pipeline first.",
        )

    latest = forecast_df.iloc[-1]
    values = _extract_station_values(latest)

    result = {
        "status": "success",
        "location": {"lat": lat, "lng": lng},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **values,
        "source_file": forecast_file.name if forecast_file else None,
        "source_stage": "stage10",
    }

    if redis_client:
        try:
            redis_client.setex(cache_key, 300, json.dumps(result))
        except Exception:
            pass

    return result


# ============================================================
# /api/predict/batch
# ============================================================

@app.get("/api/predict/batch")
def predict_batch(
    lat: str = Query(...),
    lng: str = Query(...),
):
    try:
        lats = [float(x.strip()) for x in lat.split(",") if x.strip()]
        lngs = [float(x.strip()) for x in lng.split(",") if x.strip()]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid coordinates: {e}")

    if len(lats) != len(lngs):
        raise HTTPException(status_code=400, detail="lat and lng counts must match")

    forecast_file = find_latest_file(OUTPUTS_DIR, ["regional_forecast*.csv", "forecast*.csv"])
    forecast_df = load_csv_safe(forecast_file)

    if forecast_df is None or forecast_df.empty:
        raise HTTPException(status_code=503, detail="No forecast output available.")

    latest = forecast_df.iloc[-1]
    base = _extract_station_values(latest)

    stations_out = []
    for i, (la, ln) in enumerate(zip(lats, lngs)):
        entry = dict(base)
        entry["index"] = i
        entry["lat"] = la
        entry["lng"] = ln
        stations_out.append(entry)

    return {
        "status": "success",
        "count": len(stations_out),
        "stations": stations_out,
        "source_file": forecast_file.name if forecast_file else None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# ============================================================
# /api/live — real-time from APIs
# ============================================================

@app.get("/api/live")
async def live(
    lat: float = Query(28.6139),
    lng: float = Query(77.2090),
):
    waqi_token = os.getenv("WAQI_TOKEN", "").strip()
    weatherapi_key = os.getenv("WEATHERAPI_KEY", "").strip()

    result = {
        "status": "success",
        "lat": lat, "lng": lng,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sources": {},
        "aqi": None, "pm25": None, "pm10": None,
        "no2": None, "o3": None, "co": None,
        "temperature_C": None, "humidity": None,
        "wind_speed": None, "wind_direction": None, "pbl_height_m": None,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:

        # WAQI
        if waqi_token:
            try:
                url = f"https://api.waqi.info/feed/geo:{lat};{lng}/?token={waqi_token}"
                r = await client.get(url)
                data = r.json()
                if data.get("status") == "ok":
                    iaqi = data["data"].get("iaqi", {})

                    def iaqi_val(key):
                        v = iaqi.get(key, {}).get("v")
                        return float(v) if v is not None else None

                    result["aqi"] = data["data"].get("aqi")
                    result["pm25"] = iaqi_val("pm25")
                    result["pm10"] = iaqi_val("pm10")
                    result["no2"] = iaqi_val("no2")
                    result["o3"] = iaqi_val("o3")
                    result["co"] = iaqi_val("co")
                    result["sources"]["aqi"] = "waqi"
            except Exception as e:
                logger.warning(f"WAQI failed: {e}")

        # Open-Meteo weather
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lng}"
                f"&current=temperature_2m,relative_humidity_2m,"
                f"wind_speed_10m,wind_direction_10m,surface_pressure"
                f"&hourly=boundary_layer_height"
                f"&forecast_days=1"
            )
            r = await client.get(url)
            data = r.json()
            current = data.get("current", {})

            result["temperature_C"] = current.get("temperature_2m")
            result["humidity"] = current.get("relative_humidity_2m")
            result["wind_speed"] = current.get("wind_speed_10m")
            result["wind_direction"] = current.get("wind_direction_10m")

            hourly = data.get("hourly", {})
            blh_list = hourly.get("boundary_layer_height", [])
            if blh_list:
                now_hour = datetime.utcnow().hour
                result["pbl_height_m"] = blh_list[min(now_hour, len(blh_list) - 1)]

            result["sources"]["weather"] = "open-meteo"
        except Exception as e:
            logger.warning(f"Open-Meteo failed: {e}")

        # Open-Meteo AQ fallback
        if result["pm25"] is None:
            try:
                url = (
                    f"https://air-quality-api.open-meteo.com/v1/air-quality"
                    f"?latitude={lat}&longitude={lng}"
                    f"&current=pm10,pm2_5,nitrogen_dioxide,ozone,carbon_monoxide,european_aqi"
                )
                r = await client.get(url)
                cur = r.json().get("current", {})
                result["pm25"] = cur.get("pm2_5")
                result["pm10"] = cur.get("pm10")
                result["no2"] = cur.get("nitrogen_dioxide")
                result["o3"] = cur.get("ozone")
                result["co"] = cur.get("carbon_monoxide")
                if result["aqi"] is None:
                    result["aqi"] = cur.get("european_aqi")
                result["sources"]["aqi"] = "open-meteo-air"
            except Exception as e:
                logger.warning(f"Open-Meteo AQ failed: {e}")

        # WeatherAPI fallback
        if result["temperature_C"] is None and weatherapi_key:
            try:
                url = (
                    f"https://api.weatherapi.com/v1/current.json"
                    f"?key={weatherapi_key}&q={lat},{lng}"
                )
                r = await client.get(url)
                cur = r.json().get("current", {})
                result["temperature_C"] = cur.get("temp_c")
                result["humidity"] = cur.get("humidity")
                result["wind_speed"] = cur.get("wind_kph")
                result["wind_direction"] = cur.get("wind_deg")
                result["sources"]["weather"] = "weatherapi"
            except Exception as e:
                logger.warning(f"WeatherAPI failed: {e}")

    if result["aqi"] is None and result["pm25"] is not None:
        result["aqi"] = pm25_to_aqi(float(result["pm25"]))

    for key in ["pm25", "pm10", "no2", "o3", "co", "temperature_C",
                "humidity", "wind_speed", "wind_direction", "pbl_height_m"]:
        if result[key] is not None:
            result[key] = round(float(result[key]), 2)

    if result["aqi"] is not None:
        cat = aqi_category(int(result["aqi"]))
        result["aqi_category"] = cat["category"]
        result["color"] = cat["color"]
        result["risk"] = cat["risk"]

    return result


@app.get("/api/live/batch")
async def live_batch(
    lat: str = Query(...),
    lng: str = Query(...),
):
    try:
        lats = [float(x.strip()) for x in lat.split(",") if x.strip()]
        lngs = [float(x.strip()) for x in lng.split(",") if x.strip()]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid coordinates: {e}")

    if len(lats) != len(lngs):
        raise HTTPException(status_code=400, detail="lat and lng counts must match")

    async def fetch_one(la, ln):
        try:
            return await live(lat=la, lng=ln)
        except Exception as e:
            logger.warning(f"live fetch failed for {la},{ln}: {e}")
            return {
                "status": "error", "lat": la, "lng": ln,
                "aqi": None, "pm25": None, "pm10": None,
                "no2": None, "o3": None, "co": None,
                "temperature_C": None, "humidity": None,
                "wind_speed": None, "wind_direction": None, "pbl_height_m": None,
                "error": str(e),
            }

    tasks = [fetch_one(la, ln) for la, ln in zip(lats, lngs)]
    stations_data = await asyncio.gather(*tasks)

    return {
        "status": "success",
        "count": len(stations_data),
        "stations": stations_data,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# ============================================================
# Forecast horizons
# ============================================================

def _forecast_horizon(hours: int):
    cache_key = f"forecast:{hours}h:delhi"
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    forecast_file = find_latest_file(OUTPUTS_DIR, ["regional_forecast*.csv", "forecast*.csv"])
    forecast_df = load_csv_safe(forecast_file)

    if forecast_df is None or forecast_df.empty:
        raise HTTPException(status_code=503, detail=f"No forecast for {hours}h.")

    subset = forecast_df.head(hours)
    records = []
    for _, row in subset.iterrows():
        pm25 = float(row.get("PM25", 0) or 0)
        aqi = pm25_to_aqi(pm25)
        cat = aqi_category(aqi)
        records.append({
            "time_index": int(row.get("time_index", 0) or 0),
            "pm25": round(pm25, 2),
            "pm10": round(float(row.get("PM10", 0) or 0), 2),
            "no2": round(float(row.get("NO2", 0) or 0), 2),
            "o3": round(float(row.get("O3", 0) or 0), 2),
            "co": round(float(row.get("CO", 0) or 0), 3),
            "aqi": aqi,
            "category": cat["category"],
            "color": cat["color"],
        })

    result = {
        "status": "success",
        "horizon_hours": hours,
        "count": len(records),
        "forecast": records,
    }

    if redis_client:
        try:
            redis_client.setex(cache_key, 300, json.dumps(result))
        except Exception:
            pass

    return result


@app.get("/api/forecast/24h")
def f24(): return _forecast_horizon(24)


@app.get("/api/forecast/48h")
def f48(): return _forecast_horizon(48)


@app.get("/api/forecast/72h")
def f72(): return _forecast_horizon(72)


# ============================================================
# Other endpoints
# ============================================================

@app.get("/api/heatmap")
def heatmap(region: str = Query("delhi")):
    spatial_file = find_latest_file(OUTPUTS_DIR, ["spatial_model_results*.csv", "spatial*.csv"])
    spatial_df = load_csv_safe(spatial_file)

    if spatial_df is None or spatial_df.empty:
        raise HTTPException(status_code=503, detail="No Stage 4 spatial output.")

    records = []
    for _, row in spatial_df.head(2000).iterrows():
        records.append({
            "lat": round(float(row.get("latitude", 0) or 0), 4),
            "lng": round(float(row.get("longitude", 0) or 0), 4),
            "pm25": round(float(row.get("PM25", 0) or 0), 2),
            "pm10": round(float(row.get("PM10", 0) or 0), 2),
        })

    return {"status": "success", "region": region, "count": len(records), "heatmap": records}


@app.get("/api/validation")
def validation():
    metrics_file = find_latest_file(OUTPUTS_DIR, ["validation_metrics*.csv", "validation*.csv"])
    metrics_df = load_csv_safe(metrics_file)

    if metrics_df is None or metrics_df.empty:
        raise HTTPException(status_code=503, detail="No Stage 3 validation output.")

    return {"status": "success", "metrics": metrics_df.to_dict(orient="records")}


@app.get("/api/fires")
def fires():
    fire_file = find_latest_file(OUTPUTS_DIR, ["biomass_fire_emissions*.csv", "*fire*.csv"])
    fire_df = load_csv_safe(fire_file)

    if fire_df is None or fire_df.empty:
        raise HTTPException(status_code=503, detail="No Stage 6 fire output.")

    return {"status": "success", "count": len(fire_df), "fires": fire_df.head(500).to_dict(orient="records")}


@app.get("/api/emissions")
def emissions():
    emissions_file = find_latest_file(OUTPUTS_DIR, ["spatial_emission_inventory*.csv", "*emission*.csv"])
    emissions_df = load_csv_safe(emissions_file)

    if emissions_df is None or emissions_df.empty:
        raise HTTPException(status_code=503, detail="No Stage 5 emission output.")

    return {"status": "success", "count": len(emissions_df), "emissions": emissions_df.head(1000).to_dict(orient="records")}


@app.get("/api/s3-status")
def s3_status():
    if s3_client is None:
        raise HTTPException(status_code=503, detail="S3 client not available")

    buckets = ["aqi-raw", "aqi-processed", "aqi-forecast", "aqi-models", "aqi-wrfchem", "aqi-validation"]
    result = {}
    for bucket in buckets:
        try:
            response = s3_client.list_objects_v2(Bucket=bucket, MaxKeys=20)
            contents = response.get("Contents", [])
            result[bucket] = {
                "object_count": response.get("KeyCount", 0),
                "objects": [
                    {"key": obj["Key"], "size": obj["Size"], "last_modified": obj["LastModified"].isoformat()}
                    for obj in contents
                ],
            }
        except Exception as e:
            result[bucket] = {"error": str(e)}

    return {"status": "success", "buckets": result}


# ============================================================
# POST — sync, upload, run pipeline
# ============================================================

def sync_from_s3():
    if s3_client is None:
        return {"synced": [], "errors": ["S3 client not available"]}

    synced, errors = [], []

    # Weather
    try:
        local = DATA_DIR / "meteorology" / "weather_latest.json"
        local.parent.mkdir(parents=True, exist_ok=True)
        s3_client.download_file("aqi-raw", "weather/latest.json", str(local))
        synced.append(f"weather ({local.stat().st_size} bytes)")
    except Exception as e:
        errors.append(f"weather: {e}")

    # Sensors → CSV
    try:
        local = DATA_DIR / "air_quality" / "sensors_latest.json"
        local.parent.mkdir(parents=True, exist_ok=True)
        s3_client.download_file("aqi-raw", "sensors/latest.json", str(local))
        with open(local) as f:
            data = json.load(f)
        stations_data = data.get("stations", [])
        if stations_data and pd is not None:
            csv_path = DATA_DIR / "air_quality" / "delhi_air_quality.csv"
            pd.DataFrame(stations_data).to_csv(csv_path, index=False)

            # Also write observation format for Stage 3/10
            obs_rows = []
            fetched_at = data.get("fetched_at", datetime.utcnow().isoformat())
            for s in stations_data:
                obs_rows.append({
                    "datetime": fetched_at,
                    "station": s.get("name", "unknown"),
                    "PM25": s.get("pm25"),
                    "PM10": s.get("pm10"),
                    "NO2": s.get("no2"),
                    "O3": s.get("o3"),
                    "CO": s.get("co"),
                })
            obs_path = DATA_DIR / "observations" / "air_quality.csv"
            obs_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(obs_rows).to_csv(obs_path, index=False)

            synced.append(f"sensors ({len(stations_data)} stations)")
    except Exception as e:
        errors.append(f"sensors: {e}")

    # Fires → CSV
    try:
        local = DATA_DIR / "satellite" / "fires_latest.json"
        local.parent.mkdir(parents=True, exist_ok=True)
        s3_client.download_file("aqi-raw", "fires/latest.json", str(local))
        with open(local) as f:
            data = json.load(f)
        fires_data = data.get("fires", [])
        if fires_data and pd is not None:
            csv_path = DATA_DIR / "satellite" / "fires.csv"
            pd.DataFrame(fires_data).to_csv(csv_path, index=False)
            synced.append(f"fires ({len(fires_data)} fires)")
    except Exception as e:
        errors.append(f"fires: {e}")

    return {"synced": synced, "errors": errors}


def upload_outputs_to_s3():
    if s3_client is None:
        return {"uploaded": 0, "errors": ["S3 client not available"], "details": []}

    uploaded, errors = [], []

    for filename, bucket, key in S3_UPLOAD_MAP:
        local_path = OUTPUTS_DIR / filename
        if not local_path.exists():
            continue
        try:
            s3_client.upload_file(str(local_path), bucket, key)
            uploaded.append({"file": filename, "bucket": bucket, "key": key})
        except Exception as e:
            errors.append(f"{filename} → {bucket}/{key}: {e}")

    for png in OUTPUTS_DIR.glob("*.png"):
        try:
            s3_client.upload_file(str(png), "aqi-forecast", f"plots/{png.name}")
            uploaded.append({"file": png.name, "bucket": "aqi-forecast", "key": f"plots/{png.name}"})
        except Exception as e:
            errors.append(f"{png.name}: {e}")

    return {"uploaded": len(uploaded), "errors": errors, "details": uploaded}


@app.post("/api/sync-from-s3")
def sync_from_s3_endpoint():
    result = sync_from_s3()
    return {
        "status": "success",
        "synced": result["synced"],
        "errors": result["errors"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/api/upload-outputs")
def upload_outputs_endpoint():
    result = upload_outputs_to_s3()
    return {
        "status": "success",
        "uploaded": result["uploaded"],
        "errors": result["errors"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/api/run-pipeline")
def run_pipeline(
    skip: str = Query("", description="Comma-separated stages to skip (e.g. 7,8,9)"),
    only: str = Query("", description="Comma-separated stages to run exclusively"),
    sync_s3: bool = Query(True, description="Pull live data from S3 first"),
):
    """
    Run the full Stages 1-10 pipeline.

    Default behavior:
      • Sync live data from S3
      • Run all stages 1-10
      • Upload outputs to S3

    Use skip/only to control which stages run:
        POST /api/run-pipeline?skip=7,8,9      # fast mode
        POST /api/run-pipeline?only=10         # just forecast
    """
    pipeline_script = BACKEND_DIR / "run_all_stages.py"

    if not pipeline_script.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline script not found: {pipeline_script}",
        )

    cmd = [sys.executable, str(pipeline_script)]
    if skip:
        cmd.extend(["--skip", skip])
    if only:
        cmd.extend(["--only", only])
    if not sync_s3:
        cmd.append("--no-sync")

    logger.info(f"Running pipeline: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
            timeout=7200,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Pipeline timed out (7200s)")

    if redis_client:
        try:
            for key in redis_client.scan_iter("forecast:*"):
                redis_client.delete(key)
            redis_client.delete("heatmap:latest:delhi")
        except Exception:
            pass

    return {
        "status": "success" if result.returncode == 0 else "partial",
        "returncode": result.returncode,
        "skip": skip,
        "only": only,
        "sync_s3": sync_s3,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-500:],
        "finished_at": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/api/run-forecast")
def run_forecast():
    """Stage 10 only."""
    sync_result = sync_from_s3()

    stage10_dir = STAGE_DIRS["stage10"]
    candidates = [
        stage10_dir / "main_stage10.py",
        stage10_dir / "main.py",
        stage10_dir / "run.py",
    ]
    script = next((c for c in candidates if c.exists()), None)

    if script is None:
        raise HTTPException(status_code=500, detail=f"No Stage 10 script in {stage10_dir}")

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(stage10_dir),
            capture_output=True,
            text=True,
            timeout=900,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Stage 10 timed out (900s)")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Stage 10 failed: {result.stderr[-500:]}")

    upload_result = upload_outputs_to_s3()

    if redis_client:
        try:
            redis_client.delete(
                "forecast:24h:delhi", "forecast:48h:delhi", "forecast:72h:delhi",
                "heatmap:latest:delhi",
            )
        except Exception:
            pass

    return {
        "status": "success",
        "message": "Stage 10 completed",
        "synced_from_s3": sync_result["synced"],
        "uploaded_to_s3": upload_result["uploaded"],
        "stdout_tail": result.stdout[-500:],
        "finished_at": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/api/run-stage/{stage}")
def run_stage(stage: str):
    if stage not in STAGE_DIRS:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {stage}")

    stage_dir = STAGE_DIRS[stage]
    if not stage_dir.exists():
        raise HTTPException(status_code=404, detail=f"Stage dir not found: {stage_dir}")

    n = stage.replace("stage", "")
    candidates = [
        stage_dir / f"main_stage{n}.py",
        stage_dir / f"main_{stage}.py",
        stage_dir / "main.py",
        stage_dir / "run.py",
    ]
    script = next((c for c in candidates if c.exists()), None)

    if script is None:
        raise HTTPException(status_code=500, detail=f"No entry script in {stage_dir}")

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(stage_dir),
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"{stage} timed out (1800s)")

    return {
        "status": "success" if result.returncode == 0 else "failed",
        "stage": stage,
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-500:],
        "stderr_tail": result.stderr[-500:],
    }


# ============================================================
# Startup
# ============================================================

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 70)
    logger.info("🚀 Vital 2.0 AQI API starting")
    logger.info(f"   Backend: {BACKEND_DIR}")
    logger.info(f"   AWS S3:  {s3_client is not None}")
    logger.info(f"   Redis:   {redis_client is not None}")
    logger.info("=" * 70)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
