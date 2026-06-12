from datetime import datetime
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from plant_monitor.app import SensorReading
from plant_monitor.debug import build_startup_diagnostics
from plant_monitor.env import load_env_file
from plant_monitor.logic import load_favoriot_config
from plant_monitor.notifications import detect_risk_events
from plant_monitor.settings import read_interval_seconds, telegram_config_from_env


BASE_DIR = Path(__file__).resolve().parent
load_env_file(BASE_DIR / ".env")

CSV_FILE = Path(os.getenv("CSV_FILE", str(BASE_DIR / "plant_data.csv")))
MODEL_PATH = BASE_DIR / "models" / "dryness_model.joblib"


@st.cache_data(ttl=30)
def load_data(csv_path):
    path = Path(csv_path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()

    frame = pd.read_csv(path)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    for column in ["temperature", "humidity", "soil_value", "previous_soil_value", "moisture_change_rate"]:
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
        soil_status=row.get("soil_status", ""),
        pump_status=row.get("pump_status", ""),
        ml_prediction=row.get("ml_prediction", "Unknown"),
        dry_soon_label=row.get("dry_soon_label", ""),
        notification_status=row.get("notification_status", ""),
        debug_status=row.get("debug_status", ""),
    )


def csv_health(frame):
    if frame.empty:
        return "Missing or empty CSV"
    if "timestamp" not in frame.columns or pd.isna(frame.iloc[-1]["timestamp"]):
        return "CSV timestamp missing"

    latest_time = frame.iloc[-1]["timestamp"]
    age_seconds = (pd.Timestamp.now() - latest_time).total_seconds()
    stale_after = read_interval_seconds() * 2
    if age_seconds > stale_after:
        return f"CSV stale: latest row is {int(age_seconds // 60)} minutes old"
    return "CSV fresh"


def show_alerts(reading, frame):
    health = csv_health(frame)
    if health != "CSV fresh":
        st.warning(health)
    if not reading:
        return

    events = detect_risk_events(reading)
    if not events:
        st.success("No current risk detected.")
        return

    for event in events:
        if event in {"DRY", "Dry Soon"}:
            st.error(f"Alert: {event}")
        elif event == "WET":
            st.warning("Alert: WET / overwatering risk")
        else:
            st.warning(f"Alert: {event}")


def show_charts(frame):
    if frame.empty or "timestamp" not in frame.columns:
        st.info("No chart data available yet.")
        return

    chart_frame = frame.dropna(subset=["timestamp"]).set_index("timestamp")
    if "soil_value" in chart_frame:
        st.subheader("Soil Moisture Trend")
        st.line_chart(chart_frame[["soil_value"]])
    if {"temperature", "humidity"}.issubset(chart_frame.columns):
        st.subheader("Temperature and Humidity")
        st.line_chart(chart_frame[["temperature", "humidity"]])
    if "moisture_change_rate" in chart_frame:
        st.subheader("Moisture Change Rate")
        st.line_chart(chart_frame[["moisture_change_rate"]])


def show_debug(frame):
    favoriot_config = load_favoriot_config()
    telegram_config = telegram_config_from_env()
    diagnostics = build_startup_diagnostics(
        dht_pin="from .env",
        soil_channel="from .env",
        relay_pin="from .env",
        csv_path=CSV_FILE,
        favoriot_config=favoriot_config,
        telegram_config=telegram_config,
        model_path=MODEL_PATH,
        simulation_mode=False,
    )

    st.subheader("Configuration Status")
    st.json(diagnostics)
    st.write("CSV path:", str(CSV_FILE))
    st.write("Rows loaded:", len(frame))
    st.write("Favoriot configured:", favoriot_config.is_configured)
    st.write("Telegram configured:", telegram_config.is_configured)
    st.write("Model file exists:", MODEL_PATH.exists())

    st.subheader("Latest CSV Row")
    if frame.empty:
        st.info("No data rows yet.")
    else:
        st.json(frame.iloc[-1].astype(str).to_dict())

    st.subheader("Common Wiring Hints")
    st.markdown(
        """
        - DHT11 data pin should match `DHT_PIN` such as `D4` or `D17`.
        - MCP3008 CH0 should match `SOIL_CHANNEL=0` unless the AO wire is moved.
        - Relay is active LOW: `GPIO.LOW` means pump ON, `GPIO.HIGH` means pump OFF.
        - Enable I2C for OLED and SPI for MCP3008 using `sudo raspi-config`.
        - Use `SIMULATION_MODE=true` and `RUN_ONCE=true` to test without hardware.
        """
    )


def main():
    st.set_page_config(page_title="Smart Plant Dashboard", page_icon=":seedling:", layout="wide")
    st.title("Smart Plant Monitoring Dashboard")
    st.caption("Predictive irrigation dashboard for soil dryness risk, notifications, and debugging.")

    frame = load_data(CSV_FILE)
    reading = latest_reading(frame)

    show_alerts(reading, frame)

    if reading:
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Soil Moisture", f"{reading.soil_value:.1f}%")
        col2.metric("Temperature", "N/A" if reading.temperature is None else f"{reading.temperature:.1f} C")
        col3.metric("Humidity", "N/A" if reading.humidity is None else f"{reading.humidity:.1f}%")
        col4.metric("Pump", reading.pump_status)
        col5.metric("ML Prediction", reading.ml_prediction)

    dashboard_tab, data_tab, debug_tab = st.tabs(["Dashboard", "Recent Data", "Debug"])
    with dashboard_tab:
        show_charts(frame)
    with data_tab:
        if frame.empty:
            st.info("No CSV readings found yet.")
        else:
            st.dataframe(frame.tail(50), use_container_width=True)
    with debug_tab:
        show_debug(frame)


if __name__ == "__main__":
    main()
