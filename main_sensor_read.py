import time
import board
import busio
import json
import os
from datetime import datetime

import adafruit_dht
import adafruit_ssd1306

from gpiozero import MCP3008
from PIL import Image, ImageDraw, ImageFont

import joblib
import pandas as pd

# ==========================
# HARDWARE SETUP
# ==========================
dht = adafruit_dht.DHT11(board.D4)

i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

oled.fill(0)
oled.show()

image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

soil = MCP3008(channel=5)

# ==========================
# SOIL CALIBRATION
# ==========================
DRY_LIMIT = 0.85
WET_LIMIT = 0.35
DRY_THRESHOLD = 30.0

# ==========================
# FORECAST SETUP
# ==========================
MODEL_PATH = "models/soil_forecast_sarimax.joblib"
FORECAST_HORIZONS = [4, 6, 8]
MIN_HISTORY_ROWS = 12

history = []

# ==========================
# JSON DB FILE
# ==========================
JSON_FILE = "outputs/plant_data.json"

# ==========================
# LOAD MODEL
# ==========================
def load_model(path):
    if not os.path.exists(path):
        print("[MODEL] Not found")
        return None
    try:
        return joblib.load(path)
    except Exception as e:
        print("[MODEL] Load error:", e)
        return None

model_bundle = load_model(MODEL_PATH)

# ==========================
# FORECAST FUNCTION
# ==========================
def make_forecast(model, history_rows):
    if model is None or len(history_rows) < MIN_HISTORY_ROWS:
        return None

    try:
        df = pd.DataFrame(history_rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()

        steps = max(FORECAST_HORIZONS) * 6  # assume 10-min interval
        forecast_values = model.forecast(steps=steps)

        results = {}
        for h in FORECAST_HORIZONS:
            idx = h * 6 - 1
            results[h] = round(float(forecast_values.iloc[min(idx, len(forecast_values)-1)]), 1)

        return results

    except Exception as e:
        print("[FORECAST ERROR]", e)
        return None

# ==========================
# SAFE JSON WRITE (IMPORTANT)
# ==========================
def save_json(data):
    temp_file = JSON_FILE + ".tmp"

    with open(temp_file, "w") as f:
        json.dump(data, f, indent=4)

    os.replace(temp_file, JSON_FILE)

# ==========================
# MAIN LOOP
# ==========================
print("Smart Plant System Started")

try:
    while True:

        # --------------------------
        # DHT11 READ
        # --------------------------
        try:
            temperature = dht.temperature
            humidity = dht.humidity
        except RuntimeError:
            continue

        # --------------------------
        # SOIL READ
        # --------------------------
        value = soil.value

        clamped = max(min(value, DRY_LIMIT), WET_LIMIT)
        moisture = ((DRY_LIMIT - clamped) / (DRY_LIMIT - WET_LIMIT)) * 100

        if value >= 0.70:
            soil_status = "DRY"
        elif value <= 0.40:
            soil_status = "WET"
        else:
            soil_status = "GOOD"

        # --------------------------
        # STORE HISTORY
        # --------------------------
        history.append({
            "timestamp": datetime.now(),
            "soil": moisture,
            "temp": temperature,
            "hum": humidity
        })

        if len(history) > 100:
            history.pop(0)

        # --------------------------
        # FORECAST
        # --------------------------
        forecast = make_forecast(model_bundle, history)

        # --------------------------
        # ALERTS
        # --------------------------
        alerts = {
            "dry_warning": False,
            "pump_required": False
        }

        if forecast:
            alerts["dry_warning"] = any(
                forecast[h] < DRY_THRESHOLD for h in FORECAST_HORIZONS
            )
            alerts["pump_required"] = moisture < 30

        # --------------------------
        # JSON STRUCTURE (DB)
        # --------------------------
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

            "temperature": temperature,
            "humidity": humidity,

            "soil": {
                "raw": round(value, 3),
                "moisture": round(moisture, 1),
                "status": soil_status
            },

            "forecast": forecast if forecast else {},

            "alerts": alerts
        }

        save_json(data)

        # --------------------------
        # OLED DISPLAY
        # --------------------------
        draw.rectangle((0, 0, oled.width, oled.height), fill=0)

        draw.text((0, 0), "SMART PLANT", font=font, fill=255)
        draw.text((0, 14), f"T:{temperature}C H:{humidity}%", font=font, fill=255)
        draw.text((0, 28), f"Soil:{moisture:.0f}% {soil_status}", font=font, fill=255)

        if alerts["dry_warning"]:
            draw.text((0, 46), "FORECAST DRY!", font=font, fill=255)

        oled.image(image)
        oled.show()

        # --------------------------
        # DEBUG OUTPUT
        # --------------------------
        print("--------------------------------")
        print(data)

        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopped")

finally:
    oled.fill(0)
    oled.show()