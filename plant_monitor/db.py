"""
plant_monitor/db.py
-------------------
SQLite writer for sensor readings.

Grafana can query this database via the SQLite plugin, giving true
real-time chart updates without the Streamlit page-refresh flicker.

Usage (from full_monitor.py):
    from plant_monitor.db import init_db, write_db_reading
    db_path = BASE_DIR / "sensor_data.db"
    init_db(db_path)
    ...
    write_db_reading(db_path, reading)
"""

import sqlite3
from pathlib import Path
from typing import Optional


# ── Schema ──────────────────────────────────────────────────────────────────

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sensor_readings (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp            TEXT    NOT NULL,
    temperature          REAL,
    humidity             REAL,
    soil_value           REAL,
    previous_soil_value  REAL,
    moisture_change_rate REAL,
    vpd                  REAL,
    soil_lag_1           REAL,
    soil_lag_2           REAL,
    soil_lag_3           REAL,
    soil_rolling_mean    REAL,
    soil_rate_per_hour   REAL,
    soil_status          TEXT,
    pump_status          TEXT,
    forecast_soil_4hr    REAL,
    forecast_soil_6hr    REAL,
    forecast_soil_8hr    REAL,
    forecast_risk        TEXT,
    forecast_recommendation TEXT,
    ml_prediction        TEXT,
    dry_soon_label       TEXT,
    notification_status  TEXT,
    debug_status         TEXT
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_readings (timestamp);
"""

_INSERT_SQL = """
INSERT INTO sensor_readings (
    timestamp, temperature, humidity, soil_value,
    previous_soil_value, moisture_change_rate, vpd,
    soil_lag_1, soil_lag_2, soil_lag_3, soil_rolling_mean, soil_rate_per_hour,
    soil_status, pump_status,
    forecast_soil_4hr, forecast_soil_6hr, forecast_soil_8hr,
    forecast_risk, forecast_recommendation, ml_prediction,
    dry_soon_label, notification_status, debug_status
) VALUES (
    :timestamp, :temperature, :humidity, :soil_value,
    :previous_soil_value, :moisture_change_rate, :vpd,
    :soil_lag_1, :soil_lag_2, :soil_lag_3, :soil_rolling_mean, :soil_rate_per_hour,
    :soil_status, :pump_status,
    :forecast_soil_4hr, :forecast_soil_6hr, :forecast_soil_8hr,
    :forecast_risk, :forecast_recommendation, :ml_prediction,
    :dry_soon_label, :notification_status, :debug_status
);
"""


def init_db(db_path: Path) -> None:
    """Create the database file and sensor_readings table if they don't exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(_CREATE_TABLE_SQL)
        conn.execute(_CREATE_INDEX_SQL)
        conn.commit()


def write_db_reading(db_path: Path, reading) -> None:
    """
    Append one SensorReading to the SQLite database.

    Parameters
    ----------
    db_path : Path
        Path to the SQLite database file (e.g. BASE_DIR / "sensor_data.db").
    reading : SensorReading
        The dataclass from plant_monitor.app.
    """
    row = {
        "timestamp":             reading.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "temperature":           _safe_float(reading.temperature),
        "humidity":              _safe_float(reading.humidity),
        "soil_value":            _safe_float(reading.soil_value),
        "previous_soil_value":   _safe_float(reading.previous_soil_value),
        "moisture_change_rate":  _safe_float(reading.moisture_change_rate),
        "vpd":                   _safe_float(reading.vpd),
        "soil_lag_1":            _safe_float(reading.soil_lag_1),
        "soil_lag_2":            _safe_float(reading.soil_lag_2),
        "soil_lag_3":            _safe_float(reading.soil_lag_3),
        "soil_rolling_mean":     _safe_float(reading.soil_rolling_mean),
        "soil_rate_per_hour":    _safe_float(reading.soil_rate_per_hour),
        "soil_status":           reading.soil_status or "",
        "pump_status":           reading.pump_status or "",
        "forecast_soil_4hr":     _safe_float(reading.forecast_soil_4hr),
        "forecast_soil_6hr":     _safe_float(reading.forecast_soil_6hr),
        "forecast_soil_8hr":     _safe_float(reading.forecast_soil_8hr),
        "forecast_risk":         reading.forecast_risk or "",
        "forecast_recommendation": reading.forecast_recommendation or "",
        "ml_prediction":         reading.ml_prediction or "",
        "dry_soon_label":        reading.dry_soon_label or "",
        "notification_status":   reading.notification_status or "",
        "debug_status":          reading.debug_status or "",
    }
    with sqlite3.connect(db_path) as conn:
        conn.execute(_INSERT_SQL, row)
        conn.commit()


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        result = float(value)
        return None if result != result else result  # guard NaN
    except (TypeError, ValueError):
        return None
