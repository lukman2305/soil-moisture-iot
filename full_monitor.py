import serial
import time
import Adafruit_DHT
import RPi.GPIO as GPIO
from tkinter import Tk, Label

# -----------------------------
# GPIO Setup
# -----------------------------
PUMP_PIN = 27          # GPIO pin connected to relay controlling pump
GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_PIN, GPIO.OUT)
GPIO.output(PUMP_PIN, GPIO.LOW)  # Pump OFF initially

# DHT11 Sensor
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4  # GPIO pin connected to DHT11

# -----------------------------
# Serial Setup (ESP32 soil sensor)
# -----------------------------
SERIAL_PORT = '/dev/serial0'
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    ser.reset_input_buffer()
    print("Listening for ESP32 moisture data...")
except Exception as e:
    print(f"Error opening serial port: {e}")
    ser = None

# -----------------------------
# Tkinter GUI Setup
# -----------------------------
root = Tk()
root.title("Smart Agriculture Monitor")
root.geometry("400x200")
label = Label(root, text="", font=("Arial", 16))
label.pack(pady=20)

def update_readings():
    # Read DHT11 temperature and humidity
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    if humidity is None or temperature is None:
        humidity, temperature = 0, 0

    # Read soil moisture from ESP32 serial
    soil_moisture = 0
    if ser and ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').rstrip()
        if line.startswith("MOISTURE_PCT:"):
            soil_moisture = int(line.split(":")[1])
        else:
            print(f"Raw incoming data: {line}")

    # Water pump logic: turn on if soil is dry (<40%)
    if soil_moisture < 40:
        GPIO.output(PUMP_PIN, GPIO.HIGH)  # Pump ON
        pump_status = "ON"
    else:
        GPIO.output(PUMP_PIN, GPIO.LOW)   # Pump OFF
        pump_status = "OFF"

    # Update Tkinter label
    label_text = (
        f"Temp: {temperature:.1f}°C\n"
        f"Humidity: {humidity:.1f}%\n"
        f"Soil Moisture: {soil_moisture}%\n"
        f"Pump Status: {pump_status}"
    )
    label.config(text=label_text)

    # Repeat after 2 seconds
    root.after(2000, update_readings)

# Start the GUI loop
update_readings()
root.mainloop()

# Cleanup GPIO on exit
GPIO.cleanup()
if ser and ser.is_open:
    ser.close()