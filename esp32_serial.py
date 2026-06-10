import serial
import time

serial_port = '/dev/serial0'
baud_rate = 115200

try:
    ser = serial.Serial(serial_port, baud_rate, timeout=1)
    ser.reset_input_buffer()
    print("Listening for ESP32 moisture data...")

    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            if line.startswith("MOISTURE_PCT:"):
                percentage = line.split(":")[1]
                print(f"Current Soil Moisture: {percentage}%")
            else:
                print(f"Raw incoming data: {line}")
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nProgram stopped by user.")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        