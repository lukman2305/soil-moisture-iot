import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests


CSV_HEADER = [
    "timestamp",
    "temperature",
    "humidity",
    "soil_value",
    "previous_soil_value",
    "moisture_change_rate",
    "vpd",
    "soil_lag_1",
    "soil_lag_2",
    "soil_lag_3",
    "soil_rolling_mean",
    "soil_rate_per_hour",
    "soil_status",
    "pump_status",
    "forecast_soil_4hr",
    "forecast_soil_6hr",
    "forecast_soil_8hr",
    "forecast_risk",
    "forecast_recommendation",
    "ml_prediction",
    "dry_soon_label",
    "notification_status",
    "debug_status",
]


@dataclass(frozen=True)
class SensorReading:
    timestamp: datetime
    temperature: float
    humidity: float
    soil_value: float
    previous_soil_value: float = None
    moisture_change_rate: float = 0.0
    vpd: float = None
    soil_lag_1: float = None
    soil_lag_2: float = None
    soil_lag_3: float = None
    soil_rolling_mean: float = None
    soil_rate_per_hour: float = None
    soil_status: str = ""
    pump_status: str = "OFF"
    forecast_soil_4hr: float = None
    forecast_soil_6hr: float = None
    forecast_soil_8hr: float = None
    forecast_risk: str = "Unknown"
    forecast_recommendation: str = "Forecast unavailable."
    ml_prediction: str = "Unknown"
    dry_soon_label: str = ""
    notification_status: str = ""
    debug_status: str = "OK"


def ensure_csv_header(csv_path):
    path = Path(csv_path)
    if path.exists() and path.stat().st_size > 0:
        with path.open(newline="") as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            existing_header = reader.fieldnames or []
        if all(column in existing_header for column in CSV_HEADER):
            return
        with path.open(mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_HEADER)
            writer.writeheader()
            for row in rows:
                writer.writerow({column: row.get(column, "") for column in CSV_HEADER})
        return

    with path.open(mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADER)


def _csv_value(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return str(round(value, 1))
    return str(value)


def write_csv_reading(csv_path, reading):
    with Path(csv_path).open(mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                reading.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                _csv_value(reading.temperature),
                _csv_value(reading.humidity),
                _csv_value(reading.soil_value),
                _csv_value(reading.previous_soil_value),
                _csv_value(reading.moisture_change_rate),
                _csv_value(reading.vpd),
                _csv_value(reading.soil_lag_1),
                _csv_value(reading.soil_lag_2),
                _csv_value(reading.soil_lag_3),
                _csv_value(reading.soil_rolling_mean),
                _csv_value(reading.soil_rate_per_hour),
                reading.soil_status,
                reading.pump_status,
                _csv_value(reading.forecast_soil_4hr),
                _csv_value(reading.forecast_soil_6hr),
                _csv_value(reading.forecast_soil_8hr),
                reading.forecast_risk,
                reading.forecast_recommendation,
                reading.ml_prediction,
                reading.dry_soon_label,
                reading.notification_status,
                reading.debug_status,
            ]
        )


def read_latest_soil_value(csv_path):
    path = Path(csv_path)
    if not path.exists() or path.stat().st_size == 0:
        return None

    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))

    for row in reversed(rows):
        value = row.get("soil_value")
        if value not in (None, ""):
            try:
                return float(value)
            except ValueError:
                continue
    return None


def build_favoriot_payload(device_developer_id, reading):
    return {
        "device_developer_id": device_developer_id,
        "data": {
            "temperature": reading.temperature,
            "humidity": reading.humidity,
            "soil_value": round(reading.soil_value, 1),
            "soil_status": reading.soil_status,
            "pump_status": reading.pump_status,
            "forecast_soil_4hr": reading.forecast_soil_4hr,
            "forecast_soil_6hr": reading.forecast_soil_6hr,
            "forecast_soil_8hr": reading.forecast_soil_8hr,
            "forecast_risk": reading.forecast_risk,
            "forecast_recommendation": reading.forecast_recommendation,
            "ml_prediction": reading.ml_prediction,
            "notification_status": reading.notification_status,
        },
    }


def send_to_favoriot(config, reading, post=requests.post, logger=None):
    if not config.is_configured:
        if logger:
            logger("Favoriot: skipped because API key or device developer ID is not configured")
        return False

    headers = {
        "apikey": config.api_key,
        "content-type": "application/json",
        "cache-control": "no-cache",
    }
    payload = build_favoriot_payload(config.device_developer_id, reading)

    try:
        response = post(config.url, json=payload, headers=headers, timeout=5)
    except Exception as exc:
        if logger:
            logger(f"Favoriot send failed: {exc}")
        return False

    if response.status_code in (200, 201):
        if logger:
            logger("Favoriot: data sent")
        return True

    if logger:
        logger(f"Favoriot error: {response.status_code} {response.text}")
    return False


def set_pump_output(gpio, relay_pin, pump_status):
    gpio.output(relay_pin, gpio.HIGH if pump_status == "ON" else gpio.LOW)


def format_oled_lines(reading):
    lines = ["SMART PLANT"]
    if reading.temperature is None or reading.humidity is None:
        lines.append("DHT Error")
    else:
        lines.append(f"Temp: {reading.temperature} C")
        lines.append(f"Humid: {reading.humidity}%")

    lines.append(f"Soil: {round(reading.soil_value, 1)}%")
    if reading.forecast_soil_4hr is not None or reading.forecast_soil_8hr is not None:
        f4 = "NA" if reading.forecast_soil_4hr is None else round(reading.forecast_soil_4hr, 1)
        f8 = "NA" if reading.forecast_soil_8hr is None else round(reading.forecast_soil_8hr, 1)
        lines.append(f"F4:{f4} F8:{f8} P:{reading.pump_status}")
    else:
        prediction = reading.ml_prediction if reading.ml_prediction != "Not Dry Soon" else "OK"
        lines.append(f"ML:{prediction} P:{reading.pump_status}")
    return lines
