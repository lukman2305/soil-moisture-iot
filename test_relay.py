"""
test_relay.py — Standalone relay/pump test script.
Cycles the pump ON and OFF 3 times so you can verify both states work correctly.

Usage (on Raspberry Pi):
    source testing/bin/activate
    python3 test_relay.py
"""

import time
import RPi.GPIO as GPIO

# ── Configuration ─────────────────────────────────────────────────────────────
RELAY_PIN = 16          # Must match RELAY_PIN in your .env
ON_DURATION = 3         # Seconds pump stays ON each cycle
OFF_DURATION = 3        # Seconds pump stays OFF between cycles
CYCLES = 3              # Number of ON/OFF cycles to run
# ──────────────────────────────────────────────────────────────────────────────

def relay_on(pin):
    GPIO.output(pin, GPIO.HIGH)   # Active-LOW relay: LOW = ON

def relay_off(pin):
    GPIO.output(pin, GPIO.LOW)  # Active-LOW relay: HIGH = OFF

def main():
    print("=" * 40)
    print("  Relay / Pump Test")
    print(f"  Pin: GPIO{RELAY_PIN}")
    print(f"  Cycles: {CYCLES}  |  ON: {ON_DURATION}s  |  OFF: {OFF_DURATION}s")
    print("=" * 40)

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)  # Start OFF
    print(f"\nSetup complete. Relay is OFF. Starting in 2 seconds...\n")
    time.sleep(2)

    try:
        for i in range(1, CYCLES + 1):
            print(f"[Cycle {i}/{CYCLES}] Pump ON  ...")
            relay_on(RELAY_PIN)
            time.sleep(ON_DURATION)

            print(f"[Cycle {i}/{CYCLES}] Pump OFF ...")
            relay_off(RELAY_PIN)
            time.sleep(OFF_DURATION)

        print("\nTest complete! If the pump cycled ON and OFF correctly,")
        print("your relay wiring is working perfectly.")

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")

    finally:
        relay_off(RELAY_PIN)
        GPIO.cleanup()
        print("GPIO cleaned up. Relay is OFF.")

if __name__ == "__main__":
    main()
