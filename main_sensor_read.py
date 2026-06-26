import time
import board
import busio
import adafruit_dht
import adafruit_ssd1306

from gpiozero import MCP3008
from PIL import Image, ImageDraw, ImageFont

import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime
from math import ceil

# ==========================
# DHT11 Setup
# ==========================
dht = adafruit_dht.DHT11(board.D4)

# ==========================
# OLED Setup
# ==========================
i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

oled.fill(0)
oled.show()

image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

# ==========================
# Soil Moisture Setup
# ==========================
TARGET_CHANNEL = 5

DRY_LIMIT = 0.85
WET_LIMIT = 0.35

soil = MCP3008(channel=TARGET_CHANNEL)

# ==========================
# Forecast Model Setup
# ==========================
MODEL_PATH = "models/soil_forecast_sarimax.joblib"
DRY_THRESHOLD = 30.0
FORECAST_HORIZONS = [4, 6, 8]   # hours
MIN_HISTORY_ROWS = 12             # minimum readings before forecasting

history = []   # stores past readings for the model

def load_model(path):
    p = Path(path)
    if not p.exists():
        print(f"[MODEL] File not found: {path}")
        return None
    try:
        bundle = joblib.load(p)
        print(f"[MODEL] Loaded successfully from {path}")
        return bundle
    except Exception as e:
        print(f"[MODEL] Failed to load: {e}")
        return None

def make_forecast(bundle, history_rows):
    """Given the model bundle and a list of past readings, return forecast dict."""
    if bundle is None:
        return None
    if len(history_rows) < MIN_HISTORY_ROWS:
        return None

    try:
        df = pd.DataFrame(history_rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()

        model = bundle.model if hasattr(bundle, "model") else bundle
        steps = max(FORECAST_HORIZONS) * 6   # assuming 10-min intervals = 6/hr

        forecast_values = model.forecast(steps=steps)

        results = {}
        for h in FORECAST_HORIZONS:
            step_index = h * 6 - 1   # index for that hour
            if step_index < len(forecast_values):
                results[h] = round(float(forecast_values.iloc[step_index]), 1)
            else:
                results[h] = round(float(forecast_values.iloc[-1]), 1)
        return results

    except Exception as e:
        print(f"[FORECAST] Error: {e}")
        return None

# Load the model at startup
model_bundle = load_model(MODEL_PATH)

print("===================================")
print(" Smart Plant Monitoring Started")
print(" Press Ctrl+C to stop")
print("===================================")

try:
    while True:

        # -------------------------
        # Read DHT11
        # -------------------------
        try:
            temperature = dht.temperature
            humidity = dht.humidity
        except RuntimeError:
            continue

        # -------------------------
        # Read Soil Sensor
        # -------------------------
        value = soil.value

        clamped_value = max(min(value, DRY_LIMIT), WET_LIMIT)
        moisture_pct = (
            (DRY_LIMIT - clamped_value) / (DRY_LIMIT - WET_LIMIT)
        ) * 100

        if value >= 0.70:
            soil_status = "DRY"
        elif value <= 0.40:
            soil_status = "WET"
        else:
            soil_status = "GOOD"

        # -------------------------
        # Store history for forecast
        # -------------------------
        history.append({
            "timestamp": datetime.now(),
            "soil_value": moisture_pct,
            "temperature": temperature,
            "humidity": humidity,
        })
        if len(history) > 100:
            history.pop(0)   # keep last 100 readings

        # -------------------------
        # Run Forecast
        # -------------------------
        forecast = make_forecast(model_bundle, history)

        # -------------------------
        # Terminal Output
        # -------------------------
        print("--------------------------------")
        print(f"Temperature : {temperature} °C")
        print(f"Humidity    : {humidity} %")
        print(f"Soil Raw    : {value:.3f}")
        print(f"Moisture    : {moisture_pct:.1f}%")
        print(f"Status      : {soil_status}")
        if forecast:
            print(f"Forecast 4h : {forecast.get(4, 'N/A')} %")
            print(f"Forecast 6h : {forecast.get(6, 'N/A')} %")
            print(f"Forecast 8h : {forecast.get(8, 'N/A')} %")
            for h in FORECAST_HORIZONS:
                val = forecast.get(h)
                if val is not None and val < DRY_THRESHOLD:
                    print(f"⚠️  WARNING: Soil predicted DRY in {h} hours!")
        else:
            print(f"Forecast    : collecting data... ({len(history)}/{MIN_HISTORY_ROWS})")

        # -------------------------
        # OLED Display
        # -------------------------
        draw.rectangle((0, 0, oled.width, oled.height), fill=0)

        draw.text((0, 0),  "SMART PLANT",          font=font, fill=255)
        draw.text((0, 14), f"Temp : {temperature} C", font=font, fill=255)
        draw.text((0, 28), f"Hum  : {humidity} %",   font=font, fill=255)
        draw.text((0, 42), f"Soil : {moisture_pct:.0f}%", font=font, fill=255)
        draw.text((0, 54), soil_status,             font=font, fill=255)

        oled.image(image)
        oled.show()

        time.sleep(2)

except KeyboardInterrupt:
    print("\nProgram stopped.")

finally:
    oled.fill(0)
    oled.show()
