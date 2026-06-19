import RPi.GPIO as GPIO
import time

RELAY_PIN = 16

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

try:
    while True:
        GPIO.output(RELAY_PIN, GPIO.LOW)
        print("Relay OFF")
        time.sleep(5)

        GPIO.output(RELAY_PIN, GPIO.HIGH)
        print("Relay ON")
        time.sleep(2)

except KeyboardInterrupt:
    GPIO.cleanup()
