import os
import time
from datetime import datetime
from pathlib import Path

import adafruit_dht
import adafruit_ssd1306
import board
import busio
import RPi.GPIO as GPIO
from gpiozero import MCP3008
from PIL import Image, ImageDraw, ImageFont

from plant_monitor.app import (
    SensorReading,
    ensure_csv_header,
    format_oled_lines,
    send_to_favoriot,
    set_pump_output,
    write_csv_reading,
)
from plant_monitor.env import load_env_file
from plant_monitor.logic import (
    classify_soil,
    decide_pump_status,
    load_favoriot_config,
    raw_to_moisture_percent,
)
from plant_monitor.settings import read_interval_seconds


BASE_DIR = Path(__file__).resolve().parent
load_env_file(BASE_DIR / ".env")

CSV_FILE = Path(os.getenv("CSV_FILE", str(BASE_DIR / "plant_data.csv")))
RELAY_PIN = int(os.getenv("RELAY_PIN", "18"))
SOIL_CHANNEL = int(os.getenv("SOIL_CHANNEL", "0"))
DHT_PIN = os.getenv("DHT_PIN", "D4").upper()
READ_INTERVAL_SECONDS = read_interval_seconds()

# For most analog soil sensors: raw MCP3008 value is high when dry and low when wet.
SOIL_DRY_RAW = float(os.getenv("SOIL_DRY_RAW", "1.0"))
SOIL_WET_RAW = float(os.getenv("SOIL_WET_RAW", "0.0"))
DRY_PERCENT = float(os.getenv("DRY_PERCENT", "30"))
WET_PERCENT = float(os.getenv("WET_PERCENT", "70"))


def board_pin(pin_name):
    try:
        return getattr(board, pin_name)
    except AttributeError as exc:
        raise ValueError(f"Invalid DHT_PIN '{pin_name}'. Use D4 or D17, for example.") from exc


def setup_oled():
    i2c = busio.I2C(board.SCL, board.SDA)
    oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
    oled.fill(0)
    oled.show()

    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    return oled, image, draw, font


def show_oled(oled, image, draw, font, reading):
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    for index, line in enumerate(format_oled_lines(reading)):
        draw.text((0, index * 12), line, font=font, fill=255)
    oled.image(image)
    oled.show()


def read_dht11(dht):
    # Try up to 5 times to bypass Linux microsecond interruptions
    for _ in range(5):
        try:
            return dht.temperature, dht.humidity
        except RuntimeError:
            time.sleep(0.5)
            continue
            
    print("DHT11 reading error after 5 retries")
    return None, None

def read_soil_smoothed(soil_sensor, num_samples=10, delay=0.05):
    # 1. Smoothing / Averaging Data Filter
    samples = []
    for _ in range(num_samples):
        samples.append(soil_sensor.value)
        time.sleep(delay)
    return sum(samples) / len(samples)

def build_reading(dht, soil_sensor):
    temperature, humidity = read_dht11(dht)
    
    # Get the smoothed analog reading
    avg_raw_soil = read_soil_smoothed(soil_sensor)
    
    # Convert the smoothed reading to a percentage
    soil_value = raw_to_moisture_percent(
        avg_raw_soil,
        dry_raw=SOIL_DRY_RAW,
        wet_raw=SOIL_WET_RAW,
    )
    
    # 2. Thresholding (Noise Floor) Data Filter
    # If the reading is just tiny electrical noise below 5%, force it to absolute zero
    if soil_value < 5.0:
        soil_value = 0.0
        
    soil_status = classify_soil(
        soil_value,
        dry_threshold=DRY_PERCENT,
        wet_threshold=WET_PERCENT,
    )
    pump_status = decide_pump_status(soil_status)

    reading = SensorReading(
        timestamp=datetime.now(),
        temperature=temperature,
        humidity=humidity,
        soil_value=soil_value,
        soil_status=soil_status,
        pump_status=pump_status,
    )
    
    # Return both the formatted reading object and the raw ADC value
    return reading, avg_raw_soil


def cleanup(dht, oled=None):
    print("Stopping system...")
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    GPIO.cleanup()
    dht.exit()
    if oled:
        oled.fill(0)
        oled.show()


def main():
    print("Smart plant system started. Press Ctrl+C to stop.")
    print(f"CSV file: {CSV_FILE}")
    print(f"DHT11 pin: board.{DHT_PIN}, soil channel: CH{SOIL_CHANNEL}, relay GPIO: {RELAY_PIN}")

    ensure_csv_header(CSV_FILE)
    favoriot_config = load_favoriot_config()

    dht = adafruit_dht.DHT11(board_pin(DHT_PIN))
    soil_sensor = MCP3008(channel=SOIL_CHANNEL)
    oled, image, draw, font = setup_oled()

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    GPIO.output(RELAY_PIN, GPIO.HIGH)

    try:
        while True:
            try:
                # Unpack BOTH the reading object and the raw_soil value
                reading, raw_soil = build_reading(dht, soil_sensor)
                
                set_pump_output(GPIO, RELAY_PIN, reading.pump_status)
                write_csv_reading(CSV_FILE, reading)
                send_to_favoriot(favoriot_config, reading, logger=print)
                show_oled(oled, image, draw, font, reading)

                print("----------------------")
                print("Time:", reading.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                
                # Print the raw analog value
                print("Raw soil ADC:", round(raw_soil, 3))
                
                print("Soil moisture:", round(reading.soil_value, 1), "%")
                print("Soil status:", reading.soil_status)
                print("Pump:", reading.pump_status)
                if reading.temperature is None or reading.humidity is None:
                    print("DHT11 reading error")
                else:
                    print("Temp:", reading.temperature, "C")
                    print("Humidity:", reading.humidity, "%")

            except Exception as exc:
                print(f"Loop error: {exc}")
                GPIO.output(RELAY_PIN, GPIO.HIGH)

            time.sleep(READ_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        cleanup(dht, oled)


if __name__ == "__main__":
    main()
