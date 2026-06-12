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
    "soil_status",
    "pump_status",
]


@dataclass(frozen=True)
class SensorReading:
    timestamp: datetime
    temperature: float
    humidity: float
    soil_value: float
    soil_status: str
    pump_status: str


def ensure_csv_header(csv_path):
    path = Path(csv_path)
    if path.exists() and path.stat().st_size > 0:
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
                reading.soil_status,
                reading.pump_status,
            ]
        )


def build_favoriot_payload(device_developer_id, reading):
    return {
        "device_developer_id": device_developer_id,
        "data": {
            "temperature": reading.temperature,
            "humidity": reading.humidity,
            "soil_value": round(reading.soil_value, 1),
            "soil_status": reading.soil_status,
            "pump_status": reading.pump_status,
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
    gpio.output(relay_pin, gpio.LOW if pump_status == "ON" else gpio.HIGH)


def format_oled_lines(reading):
    lines = ["SMART PLANT"]
    if reading.temperature is None or reading.humidity is None:
        lines.append("DHT Error")
    else:
        lines.append(f"Temp: {reading.temperature} C")
        lines.append(f"Humid: {reading.humidity}%")

    lines.append(f"Soil: {round(reading.soil_value, 1)}%")
    lines.append(f"{reading.soil_status} P:{reading.pump_status}")
    return lines
