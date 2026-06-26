import time
import board
import busio
import adafruit_dht
import adafruit_ssd1306

from gpiozero import MCP3008
from PIL import Image, ImageDraw, ImageFont

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
TARGET_CHANNEL = 5      # Change if needed

DRY_LIMIT = 0.85
WET_LIMIT = 0.35

soil = MCP3008(channel=TARGET_CHANNEL)

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
            # DHT11 occasionally fails
            continue

        # -------------------------
        # Read Soil Sensor
        # -------------------------
        value = soil.value

        clamped_value = max(min(value, DRY_LIMIT), WET_LIMIT)

        moisture_pct = (
            (DRY_LIMIT - clamped_value)
            / (DRY_LIMIT - WET_LIMIT)
        ) * 100

        if value >= 0.70:
            soil_status = "DRY"
        elif value <= 0.40:
            soil_status = "WET"
        else:
            soil_status = "GOOD"

        # -------------------------
        # Terminal Output
        # -------------------------
        print("--------------------------------")
        print(f"Temperature : {temperature} °C")
        print(f"Humidity    : {humidity} %")
        print(f"Soil Raw    : {value:.3f}")
        print(f"Moisture    : {moisture_pct:.1f}%")
        print(f"Status      : {soil_status}")

        # -------------------------
        # OLED Display
        # -------------------------
        draw.rectangle((0, 0, oled.width, oled.height), fill=0)

        draw.text((0, 0), "SMART PLANT", font=font, fill=255)
        draw.text((0, 14), f"Temp : {temperature} C", font=font, fill=255)
        draw.text((0, 28), f"Hum  : {humidity} %", font=font, fill=255)
        draw.text((0, 42), f"Soil : {moisture_pct:.0f}%", font=font, fill=255)
        draw.text((0, 54), soil_status, font=font, fill=255)

        oled.image(image)
        oled.show()

        time.sleep(2)

except KeyboardInterrupt:
    print("\nProgram stopped.")

finally:
    oled.fill(0)
    oled.show()
