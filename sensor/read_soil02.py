from gpiozero import MCP3008
import time

# !!! CHANGE THIS VALUE !!! 
# Set to 0 if wired to Pin 1. Set to 5 if wired to Pin 6.
TARGET_CHANNEL = 5 

# Your calibrated limits (tweak these after watching the raw values)
DRY_LIMIT = 0.85
WET_LIMIT = 0.35

soil = MCP3008(channel=TARGET_CHANNEL)

print(f"Monitoring Soil Sensor on MCP3008 Channel {TARGET_CHANNEL}...")

try:
    while True:
        value = soil.value
        
        # Calculate clean percentage (Inverted logic: Dry = 0%, Wet = 100%)
        clamped_value = max(min(value, DRY_LIMIT), WET_LIMIT)
        moisture_pct = ((DRY_LIMIT - clamped_value) / (DRY_LIMIT - WET_LIMIT)) * 100
        
        print(f"Raw Value: {value:.4f} | Moisture: {moisture_pct:.1f}% | Status: ", end="")

        # Threshold triggers based on the raw voltage fraction
        if value >= 0.70:
            print("DRY ⚠️")
        elif value <= 0.40:
            print("WET 🌊")
        else:
            print("OPTIMAL ✅")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopped.")
