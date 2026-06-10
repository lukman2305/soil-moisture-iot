import time
import csv
import Adafruit_DHT
import RPi.GPIO as GPIO
from tkinter import Tk, Label
import busio
import digitalio
import board
from adafruit_mcp3xxx.mcp3008 import MCP3008
from adafruit_mcp3xxx.analog_in import AnalogIn

# -----------------------------
# GPIO Setup
# -----------------------------
PUMP_PIN = 27
GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_PIN, GPIO.OUT)
GPIO.output(PUMP_PIN, GPIO.LOW)  # Pump OFF initially

# DHT11 Sensor
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4

# -----------------------------
# MCP3008 Setup for Soil Moisture
# -----------------------------
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D8)  # CE0
mcp = MCP3008(spi, cs)
soil_channel = AnalogIn(mcp, 0)

# Calibration
DRY_VALUE = 35000   # ADC value when dry
WET_VALUE = 15000   # ADC value when wet

# -----------------------------
# CSV Logging Setup
# -----------------------------
CSV_FILE = "sensor_readings.csv"

# Create CSV with headers if not exist
with open(CSV_FILE, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Temperature_C", "Humidity_%", "Soil_Moisture_%", "Pump_Status"])

# -----------------------------
# Tkinter GUI Setup
# -----------------------------
root = Tk()
root.title("Smart Agriculture Monitor")
root.geometry("400x200")
label = Label(root, text="", font=("Arial", 16))
label.pack(pady=20)

def update_readings():
    # Read DHT11
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    if humidity is None or temperature is None:
        humidity, temperature = 0, 0

    # Read Soil Moisture from MCP3008
    raw_value = soil_channel.value
    raw_value = min(max(raw_value, WET_VALUE), DRY_VALUE)
    soil_moisture = int((DRY_VALUE - raw_value) / (DRY_VALUE - WET_VALUE) * 100)

    # Pump logic
    if soil_moisture < 40:
        GPIO.output(PUMP_PIN, GPIO.HIGH)
        pump_status = "ON"
    else:
        GPIO.output(PUMP_PIN, GPIO.LOW)
        pump_status = "OFF"

    # Update GUI
    label_text = (
        f"Temp: {temperature:.1f}°C\n"
        f"Humidity: {humidity:.1f}%\n"
        f"Soil Moisture: {soil_moisture}%\n"
        f"Pump Status: {pump_status}"
    )
    label.config(text=label_text)

    # Save reading to CSV
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, temperature, humidity, soil_moisture, pump_status])

    # Repeat after 2 seconds
    root.after(2000, update_readings)

# Start GUI loop
update_readings()
root.mainloop()

# Cleanup GPIO on exit
GPIO.cleanup()