"""
all_handlers.py — Consolidated Lambda handlers for Vital 2.0

Handlers:
    1. ingest-fires          — fetch NASA FIRMS fires
    2. ingest-sensors        — fetch WAQI + CPCB AQI
    3. ingest-weather        — fetch WeatherAPI + Open-Meteo
    4. forecast-trigger      — POST to EC2 /api/run-pipeline
    5. training-launch-ec2   — launch spot EC2 for WRF-Chem
    6. training-validate     — check S3 for model artifacts
    7. training-update       — SSM command to reload inference
    8. training-terminate    — terminate training EC2
"""

import json
import os
import csv
import io
import logging
import urllib.request
import urllib.parse
from datetime import datetime

import boto3

# ============================================================
# Setup
# ============================================================

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "us-east-1")

_s3 = None
_dynamodb = None
_ec2 = None
_ssm = None


def s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=REGION)
    return _s3


def dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=REGION)
    return _dynamodb


def ec2():
    global _ec2
    if _ec2 is None:
        _ec2 = boto3.client("ec2", region_name=REGION)
    return _ec2


def ssm():
    global _ssm
    if _ssm is None:
        _ssm = boto3.client("ssm", region_name=REGION)
    return _ssm


# ============================================================
# Shared helpers
# ============================================================

def http_get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def http_post(url, body=None, headers=None, timeout=600):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers=headers or {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def save_to_s3(bucket, key, content, content_type="application/json"):
    if isinstance(content, str):
        content = content.encode("utf-8")
    s3().put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
    logger.info(f"✅ S3 write: s3://{bucket}/{key}")


def now_utc():
    return datetime.utcnow().isoformat() + "Z"


def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ============================================================
# 1. ingest-fires
# ============================================================

def ingest_fires(event, context):
    logger.info("🔥 ingest-fires triggered")

    api_key = os.environ.get("NASA_FIRMS_API_KEY", "").strip()
    raw_bucket = os.environ.get("S3_RAW_BUCKET", "aqi-raw")

    if not api_key:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "NASA_FIRMS_API_KEY not set"}),
        }

    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{api_key}/VIIRS_SNPP_NRT/"
        f"75.5,27.0,79.5,30.5/1"
    )

    try:
        csv_text = http_get(url, timeout=60)
    except Exception as e:
        logger.error(f"NASA FIRMS fetch failed: {e}")
        return {"statusCode": 502, "body": json.dumps({"error": str(e)})}

    if not csv_text.strip() or csv_text.strip().startswith("{"):
        return {
            "statusCode": 502,
            "body": json.dumps({
                "error": "FIRMS returned non-CSV",
                "response_preview": csv_text[:200],
            }),
        }

    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    logger.info(f"Fetched {len(rows)} fire detections")

    fires = []
    for r in rows:
        lat = safe_float(r.get("latitude"))
        lon = safe_float(r.get("longitude"))
        if lat is None or lon is None:
            continue
        fires.append({
            "latitude": lat,
            "longitude": lon,
            "acq_date": r.get("acq_date", ""),
            "acq_time": r.get("acq_time", ""),
            "frp": safe_float(r.get("frp")) or 0,
            "confidence": r.get("confidence", "unknown"),
            "satellite": r.get("satellite", "unknown"),
        })

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    payload = {
        "fetched_at": now_utc(),
        "count": len(fires),
        "bbox": {"west": 75.5, "south": 27.0, "east": 79.5, "north": 30.5},
        "fires": fires,
    }

    save_to_s3(raw_bucket, f"fires/{timestamp}.json", json.dumps(payload))
    save_to_s3(raw_bucket, "fires/latest.json", json.dumps(payload))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "success",
            "fires_fetched": len(fires),
            "s3_key": f"fires/{timestamp}.json",
            "timestamp": now_utc(),
        }),
    }


# ============================================================
# 2. ingest-sensors
# ============================================================

def ingest_sensors(event, context):
    logger.info("📡 ingest-sensors triggered")

    waqi_token = os.environ.get("WAQI_TOKEN", "").strip()
    cpcb_key = os.environ.get("CPCB_API_KEY", "").strip()
    raw_bucket = os.environ.get("S3_RAW_BUCKET", "aqi-raw")

    delhi_stations = [
        {"name": "New Delhi", "lat": 28.6139, "lon": 77.2090},
        {"name": "Anand Vihar", "lat": 28.6468, "lon": 77.3164},
        {"name": "ITO", "lat": 28.6298, "lon": 77.2423},
        {"name": "RK Puram", "lat": 28.5633, "lon": 77.1769},
        {"name": "Dwarka", "lat": 28.5704, "lon": 77.0653},
        {"name": "Rohini", "lat": 28.7344, "lon": 77.0895},
        {"name": "Noida", "lat": 28.5355, "lon": 77.3910},
        {"name": "Gurgaon", "lat": 28.4595, "lon": 77.0266},
        {"name": "Jahangirpuri", "lat": 28.7286, "lon": 77.1637},
        {"name": "Faridabad", "lat": 28.4089, "lon": 77.3178},
    ]

    results = []

    for station in delhi_stations:
        rec = {
            "name": station["name"],
            "lat": station["lat"],
            "lon": station["lon"],
            "pm25": None,
            "pm10": None,
            "no2": None,
            "o3": None,
            "co": None,
            "aqi": None,
            "source": None,
        }

        # WAQI
        if waqi_token:
            try:
                url = (
                    f"https://api.waqi.info/feed/geo:"
                    f"{station['lat']};{station['lon']}/"
                    f"?token={waqi_token}"
                )
                data = json.loads(http_get(url, timeout=10))
                if data.get("status") == "ok":
                    iaqi = data["data"].get("iaqi", {})

                    def iaqi_val(k):
                        v = iaqi.get(k, {}).get("v")
                        return float(v) if v is not None else None

                    rec["pm25"] = iaqi_val("pm25")
                    rec["pm10"] = iaqi_val("pm10")
                    rec["no2"] = iaqi_val("no2")
                    rec["o3"] = iaqi_val("o3")
                    rec["co"] = iaqi_val("co")
                    rec["aqi"] = data["data"].get("aqi")
                    rec["source"] = "waqi"
            except Exception as e:
                logger.warning(f"WAQI failed for {station['name']}: {e}")

        results.append(rec)

    # Open-Meteo fallback for stations WAQI missed
    for rec in results:
        if rec["pm25"] is not None:
            continue
        try:
            url = (
                f"https://air-quality-api.open-meteo.com/v1/air-quality"
                f"?latitude={rec['lat']}&longitude={rec['lon']}"
                f"&current=pm10,pm2_5,nitrogen_dioxide,ozone,carbon_monoxide,european_aqi"
            )
            data = json.loads(http_get(url, timeout=10))
            cur = data.get("current", {})
            rec["pm25"] = cur.get("pm2_5")
            rec["pm10"] = cur.get("pm10")
            rec["no2"] = cur.get("nitrogen_dioxide")
            rec["o3"] = cur.get("ozone")
            rec["co"] = cur.get("carbon_monoxide")
            rec["aqi"] = cur.get("european_aqi")
            rec["source"] = "open-meteo"
        except Exception as e:
            logger.warning(f"Open-Meteo fallback failed for {rec['name']}: {e}")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    payload = {
        "fetched_at": now_utc(),
        "count": len(results),
        "stations": results,
    }

    save_to_s3(raw_bucket, f"sensors/{timestamp}.json", json.dumps(payload))
    save_to_s3(raw_bucket, "sensors/latest.json", json.dumps(payload))

    with_data = sum(1 for s in results if s["pm25"] is not None)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "success",
            "stations_checked": len(results),
            "stations_with_data": with_data,
            "timestamp": now_utc(),
        }),
    }


# ============================================================
# 3. ingest-weather
# ============================================================

def ingest_weather(event, context):
    logger.info("🌤️ ingest-weather triggered")

    weatherapi_key = os.environ.get("WEATHERAPI_KEY", "").strip()
    raw_bucket = os.environ.get("S3_RAW_BUCKET", "aqi-raw")

    lat, lon = 28.6139, 77.2090

    result = {
        "fetched_at": now_utc(),
        "location": {"lat": lat, "lon": lon},
        "sources": {},
    }

    # WeatherAPI
    if weatherapi_key:
        try:
            url = (
                f"https://api.weatherapi.com/v1/current.json"
                f"?key={weatherapi_key}&q={lat},{lon}"
            )
            data = json.loads(http_get(url, timeout=10))
            current = data.get("current", {})
            result["sources"]["weatherapi"] = {
                "temperature_C": current.get("temp_c"),
                "humidity": current.get("humidity"),
                "wind_speed_kmh": current.get("wind_kph"),
                "wind_direction": current.get("wind_degree"),
                "pressure_mb": current.get("pressure_mb"),
                "condition": current.get("condition", {}).get("text"),
            }
        except Exception as e:
            logger.warning(f"WeatherAPI failed: {e}")
            result["sources"]["weatherapi"] = {"error": str(e)}

    # Open-Meteo (always)
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,"
            f"wind_speed_10m,wind_direction_10m,pressure_msl"
            f"&hourly=boundary_layer_height"
            f"&forecast_days=2"
        )
        data = json.loads(http_get(url, timeout=10))
        current = data.get("current", {})
        hourly = data.get("hourly", {})

        pbl_hourly = {}
        for t, v in zip(hourly.get("time", []), hourly.get("boundary_layer_height", [])):
            pbl_hourly[t] = v

        result["sources"]["open_meteo"] = {
            "temperature_C": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
            "pressure_mb": current.get("pressure_msl"),
            "pbl_hourly": pbl_hourly,
        }
    except Exception as e:
        logger.warning(f"Open-Meteo failed: {e}")
        result["sources"]["open_meteo"] = {"error": str(e)}

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    save_to_s3(raw_bucket, f"weather/{timestamp}.json", json.dumps(result))
    save_to_s3(raw_bucket, "weather/latest.json", json.dumps(result))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "success",
            "sources": list(result["sources"].keys()),
            "timestamp": now_utc(),
        }),
    }


# ============================================================
# 4. forecast-trigger
# ============================================================

def forecast_trigger(event, context):
    """
    Trigger Stages 1-10 pipeline on EC2.
    Default skips 1,2,3,7,8,9 (heavy/optional stages).
    """
    logger.info("🚀 forecast-trigger triggered")

    ec2_api = os.environ.get("EC2_API_URL", "http://32.196.37.69:3000")
    skip_stages = os.environ.get("SKIP_STAGES", "1,2,3,7,8,9")

    url = f"{ec2_api}/api/run-pipeline"
    if skip_stages:
        url += f"?skip={skip_stages}"

    logger.info(f"Calling: {url}")

    try:
        response_text = http_post(url, body={}, timeout=600)
        response = json.loads(response_text)
        logger.info(f"Pipeline status: {response.get('status')}")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "triggered": True,
                "skip_stages": skip_stages,
                "pipeline_status": response.get("status"),
                "returncode": response.get("returncode"),
                "timestamp": now_utc(),
            }),
        }
    except Exception as e:
        logger.error(f"Pipeline trigger failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "triggered": False,
                "error": str(e),
                "timestamp": now_utc(),
            }),
        }


# ============================================================
# 5. training-launch-ec2
# ============================================================

def training_launch_ec2(event, context):
    logger.info("🖥️ training-launch-ec2 triggered")

    ami = os.environ.get("TRAINING_AMI_ID", "").strip()
    instance_type = os.environ.get("TRAINING_INSTANCE_TYPE", "g4dn.xlarge")
    subnet_id = os.environ.get("TRAINING_SUBNET_ID", "").strip()
    sg_id = os.environ.get("TRAINING_SECURITY_GROUP_ID", "").strip()
    key_name = os.environ.get("TRAINING_KEY_NAME", "").strip()
    iam_profile = os.environ.get("TRAINING_IAM_PROFILE", "").strip()

    if not ami or not subnet_id or not sg_id:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Missing TRAINING_AMI_ID, TRAINING_SUBNET_ID, or TRAINING_SECURITY_GROUP_ID",
            }),
        }

    user_data = """#!/bin/bash
set -e
cd /home/ubuntu
if [ ! -d /home/ubuntu/vital2.0 ]; then
    git clone https://github.com/YashRawate/Vital2.O.git /home/ubuntu/vital2.0
fi
cd /home/ubuntu/vital2.0/Backend
python3 run_all_stages.py --skip 1,2,3 || true
echo "done" > /tmp/training.done
aws s3 cp /tmp/training.done s3://aqi-models/training-complete.done || true
"""

    try:
        response = ec2().run_instances(
            ImageId=ami,
            InstanceType=instance_type,
            KeyName=key_name or None,
            MinCount=1,
            MaxCount=1,
            SubnetId=subnet_id,
            SecurityGroupIds=[sg_id],
            IamInstanceProfile={"Name": iam_profile} if iam_profile else None,
            InstanceMarketOptions={
                "MarketType": "spot",
                "SpotOptions": {
                    "MaxPrice": "0.30",
                    "SpotInstanceType": "one-time",
                },
            },
            UserData=user_data,
            TagSpecifications=[{
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": "aqi-training"},
                    {"Key": "Purpose", "Value": "WRF-Chem training"},
                ],
            }],
        )

        instance_id = response["Instances"][0]["InstanceId"]

        return {
            "statusCode": 200,
            "body": json.dumps({
                "instance_id": instance_id,
                "instance_type": instance_type,
                "status": "launched",
                "timestamp": now_utc(),
            }),
        }
    except Exception as e:
        logger.error(f"EC2 launch failed: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# ============================================================
# 6. training-validate
# ============================================================

def training_validate(event, context):
    logger.info("✅ training-validate triggered")

    models_bucket = os.environ.get("S3_MODELS_BUCKET", "aqi-models")

    try:
        response = s3().list_objects_v2(
            Bucket=models_bucket,
            Prefix="emulator-",
            MaxKeys=10,
        )
        contents = response.get("Contents", [])

        if not contents:
            return {
                "statusCode": 404,
                "body": json.dumps({
                    "valid": False,
                    "error": "No model artifacts found",
                }),
            }

        latest = sorted(contents, key=lambda x: x["LastModified"], reverse=True)[0]

        return {
            "statusCode": 200,
            "body": json.dumps({
                "valid": True,
                "model_key": latest["Key"],
                "last_modified": latest["LastModified"].isoformat(),
                "timestamp": now_utc(),
            }),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# ============================================================
# 7. training-update
# ============================================================

def training_update(event, context):
    logger.info("🔄 training-update triggered")

    instance_id = os.environ.get("INFERENCE_INSTANCE_ID", "").strip()

    if not instance_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "INFERENCE_INSTANCE_ID not set"}),
        }

    try:
        response = ssm().send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={
                "commands": [
                    "cd /vital2.0/Backend",
                    "source venv/bin/activate",
                    "sudo systemctl restart aqi-api",
                    "echo 'Model reloaded'",
                ],
            },
            Comment="Reload model after training",
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "command_id": response["Command"]["CommandId"],
                "instance_id": instance_id,
                "status": "sent",
                "timestamp": now_utc(),
            }),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# ============================================================
# 8. training-terminate
# ============================================================

def training_terminate(event, context):
    logger.info("🛑 training-terminate triggered")

    instance_id = None
    if isinstance(event, dict):
        instance_id = (
            event.get("instance_id")
            or event.get("detail", {}).get("instance_id")
        )

    if not instance_id:
        instance_id = os.environ.get("TRAINING_INSTANCE_ID", "").strip()

    if not instance_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No instance_id provided"}),
        }

    try:
        ec2().terminate_instances(InstanceIds=[instance_id])

        return {
            "statusCode": 200,
            "body": json.dumps({
                "terminated": instance_id,
                "timestamp": now_utc(),
            }),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# ============================================================
# Router — for testing as one Lambda
# ============================================================

HANDLERS = {
    "ingest-fires": ingest_fires,
    "ingest-sensors": ingest_sensors,
    "ingest-weather": ingest_weather,
    "forecast-trigger": forecast_trigger,
    "training-launch-ec2": training_launch_ec2,
    "training-validate": training_validate,
    "training-update": training_update,
    "training-terminate": training_terminate,
}


def router(event, context):
    function_name = os.environ.get("FUNCTION_NAME", "")
    handler = HANDLERS.get(function_name)

    if handler is None:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": f"Unknown function: {function_name}",
                "available": list(HANDLERS.keys()),
            }),
        }

    return handler(event, context)
