"""
test_soil.py — Standalone soil moisture sensor test script.
Continuously reads and prints the raw value from the MCP3008 chip.

Usage (on Raspberry Pi):
    source testing/bin/activate
    python3 test_soil.py
"""

import time
import os
from gpiozero import MCP3008

# ── Configuration ─────────────────────────────────────────────────────────────
SOIL_CHANNEL = 5  # Must match the channel your sensor is plugged into on the MCP3008
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  Soil Moisture Sensor Test")
    print(f"  MCP3008 Channel: {SOIL_CHANNEL}")
    print("  Press Ctrl+C to stop.")
    print("=" * 50)
    print("\nReading data... Try dipping the sensor in water to see the values change!\n")

    try:
        # Initialize the MCP3008 sensor on the specified channel
        soil_sensor = MCP3008(channel=SOIL_CHANNEL)
        
        # Loop forever, reading and printing the value every 1 second
        while True:
            # The MCP3008 returns a value between 0.0 and 1.0
            raw_value = soil_sensor.value
            
            # Print the raw value, formatted to 3 decimal places
            print(f"Raw Soil Value: {raw_value:.3f}")
            
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError reading sensor: {e}")
    finally:
        print("Closing test.")

if __name__ == "__main__":
    main()
