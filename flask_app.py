import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import yaml
import bcrypt
from flask import Flask, request, jsonify, session, send_from_directory

from plant_monitor.app import SensorReading
from plant_monitor.env import load_env_file
from plant_monitor.forecast import (
    FORECAST_RISK_DRY,
    FORECAST_UNKNOWN,
    forecast_soil_moisture,
    load_forecast_model,
)
from plant_monitor.logic import load_favoriot_config
from plant_monitor.notifications import detect_risk_events
from plant_monitor.settings import telegram_config_from_env

# ---- Configuration ----
BASE_DIR = Path(__file__).resolve().parent
load_env_file(BASE_DIR / ".env")

_truthy = lambda v: str(v).strip().lower() in {"1", "true", "yes", "on"}
_sim_mode = _truthy(os.getenv("SIMULATION_MODE", "false"))
_demo_mode = _truthy(os.getenv("DEMO_MODE", "false"))
if _sim_mode:
    CSV_FILE = BASE_DIR / "sim_data.csv"
elif _demo_mode:
    CSV_FILE = BASE_DIR / "demo_data.csv"
else:
    CSV_FILE = Path(os.getenv("CSV_FILE", str(BASE_DIR / "plant_data.csv")))

MODEL_PATH = Path(os.getenv("FORECAST_MODEL_PATH", str(BASE_DIR / "models" / "soil_forecast_sarimax.joblib")))
AUTH_CONFIG_PATH = BASE_DIR / "auth_config.yaml"
FORECAST_MIN_ROWS = int(os.getenv("FORECAST_MIN_ROWS", "4"))
FORECAST_RECENT_AVERAGE_HOURS = float(os.getenv("FORECAST_RECENT_AVERAGE_HOURS", "1"))
FORECAST_DRY_PERCENT = float(os.getenv("FORECAST_DRY_PERCENT", "30"))

NUMERIC_COLUMNS = [
    "temperature", "humidity", "soil_value", "previous_soil_value",
    "moisture_change_rate", "vpd", "soil_lag_1", "soil_lag_2", "soil_lag_3",
    "soil_rolling_mean", "soil_rate_per_hour", "forecast_soil_4hr",
    "forecast_soil_6hr", "forecast_soil_8hr",
]

# ---- Flask Setup ----
# Serve static files from the 'public' directory
app = Flask(__name__, static_folder="public", static_url_path="")
# Use a secure random secret key in production, but hardcoded here for simplicity across reboots
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-iot-key-1234")


# ---- Helpers ----
def load_data(csv_path):
    path = Path(csv_path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()

    frame = pd.read_csv(path)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], format="mixed", errors="coerce")
        frame = frame.dropna(subset=["timestamp"]).reset_index(drop=True)
    for column in NUMERIC_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame

def latest_reading(frame):
    if frame.empty:
        return None
    row = frame.iloc[-1].to_dict()
    timestamp = row.get("timestamp")
    if pd.isna(timestamp):
        timestamp = datetime.now()
    elif hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()
        
    return SensorReading(
        timestamp=timestamp,
        temperature=None if pd.isna(row.get("temperature")) else row.get("temperature"),
        humidity=None if pd.isna(row.get("humidity")) else row.get("humidity"),
        soil_value=0.0 if pd.isna(row.get("soil_value")) else row.get("soil_value"),
        previous_soil_value=None if pd.isna(row.get("previous_soil_value")) else row.get("previous_soil_value"),
        moisture_change_rate=0.0 if pd.isna(row.get("moisture_change_rate")) else row.get("moisture_change_rate"),
        vpd=None if pd.isna(row.get("vpd")) else row.get("vpd"),
        soil_lag_1=None if pd.isna(row.get("soil_lag_1")) else row.get("soil_lag_1"),
        soil_lag_2=None if pd.isna(row.get("soil_lag_2")) else row.get("soil_lag_2"),
        soil_lag_3=None if pd.isna(row.get("soil_lag_3")) else row.get("soil_lag_3"),
        soil_rolling_mean=None if pd.isna(row.get("soil_rolling_mean")) else row.get("soil_rolling_mean"),
        soil_rate_per_hour=None if pd.isna(row.get("soil_rate_per_hour")) else row.get("soil_rate_per_hour"),
        soil_status=row.get("soil_status", ""),
        pump_status=row.get("pump_status", ""),
        forecast_soil_4hr=None if pd.isna(row.get("forecast_soil_4hr")) else row.get("forecast_soil_4hr"),
        forecast_soil_6hr=None if pd.isna(row.get("forecast_soil_6hr")) else row.get("forecast_soil_6hr"),
        forecast_soil_8hr=None if pd.isna(row.get("forecast_soil_8hr")) else row.get("forecast_soil_8hr"),
        forecast_risk=row.get("forecast_risk", FORECAST_UNKNOWN),
        forecast_recommendation=row.get("forecast_recommendation", "Forecast unavailable."),
        ml_prediction=row.get("ml_prediction", "Unknown"),
        dry_soon_label=row.get("dry_soon_label", ""),
        notification_status=row.get("notification_status", ""),
        debug_status=row.get("debug_status", ""),
    )

def forecast_from_history(frame):
    bundle = load_forecast_model(MODEL_PATH)
    if not bundle.is_ready or frame.empty:
        return None
    return forecast_soil_moisture(
        bundle,
        frame,
        horizons_hours=[4, 6, 8],
        recent_average_hours=FORECAST_RECENT_AVERAGE_HOURS,
        dry_threshold=FORECAST_DRY_PERCENT,
        control_mode=os.getenv("ML_CONTROL_MODE", "recommend"),
    )

def _load_auth_config() -> dict:
    if not AUTH_CONFIG_PATH.exists():
        return {}
    with open(AUTH_CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}

def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

# ---- Routes ----

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")
    
    config = _load_auth_config()
    users = config.get("credentials", {}).get("usernames", {})
    user_info = users.get(username)
    
    if user_info and isinstance(user_info, dict) and _verify_password(password, user_info.get("password", "")):
        session["authenticated"] = True
        session["username"] = username
        session["user_name"] = user_info.get("name", username)
        return jsonify({"success": True, "name": session["user_name"]})
    
    return jsonify({"success": False, "message": "Invalid username or password"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/auth_status", methods=["GET"])
def auth_status():
    if session.get("authenticated"):
        return jsonify({"authenticated": True, "name": session.get("user_name")})
    return jsonify({"authenticated": False}), 401

@app.route("/api/data", methods=["GET"])
def get_data():
    if not session.get("authenticated"):
        return jsonify({"error": "Unauthorized"}), 401
        
    frame = load_data(CSV_FILE)
    reading = latest_reading(frame)
    forecast_result = forecast_from_history(frame)
    
    alerts = []
    if reading:
        events = detect_risk_events(reading)
        if reading.forecast_risk == FORECAST_UNKNOWN:
            alerts.append("Forecast unavailable. Collect more real sensor rows or train the SARIMAX model.")
        
        dry_horizon = ""
        if reading.forecast_soil_4hr is not None and reading.forecast_soil_4hr < FORECAST_DRY_PERCENT:
            dry_horizon = " in 4 hours"
        elif reading.forecast_soil_6hr is not None and reading.forecast_soil_6hr < FORECAST_DRY_PERCENT:
            dry_horizon = " in 6 hours"
        elif reading.forecast_soil_8hr is not None and reading.forecast_soil_8hr < FORECAST_DRY_PERCENT:
            dry_horizon = " in 8 hours"
            
        for event in events:
            if event not in {"DRY", "Dry Soon", "Forecast Dry", "WET"}:
                alerts.append(f"Alert: {event}")
            elif event == "WET":
                alerts.append("Alert: WET / overwatering risk")
                
        if "DRY" in events:
            alerts.append("🚨 Alert: Soil is currently DRY!")
        elif reading.forecast_risk == FORECAST_RISK_DRY or "Forecast Dry" in events or "Dry Soon" in events:
            alerts.append(f"⚠️ Forecast Alert: Soil moisture is predicted to fall below the dry threshold{dry_horizon}.")
    
    # Process history for charts (last 100 points)
    history_data = []
    if not frame.empty:
        chart_frame = frame.tail(100).fillna(0)
        for _, row in chart_frame.iterrows():
            history_data.append({
                "time": row["timestamp"].strftime("%H:%M:%S") if pd.notna(row["timestamp"]) else "",
                "soil_value": row.get("soil_value", 0),
                "temperature": row.get("temperature", 0),
                "humidity": row.get("humidity", 0)
            })
            
    reading_dict = {}
    if reading:
        reading_dict = {
            "soil_value": reading.soil_value,
            "soil_status": reading.soil_status,
            "forecast_soil_4hr": reading.forecast_soil_4hr,
            "forecast_soil_6hr": reading.forecast_soil_6hr,
            "forecast_soil_8hr": reading.forecast_soil_8hr,
            "pump_status": reading.pump_status,
        }

    return jsonify({
        "reading": reading_dict,
        "alerts": alerts,
        "history": history_data,
        "dry_threshold": FORECAST_DRY_PERCENT
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
