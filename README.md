# Raspberry Pi 400 Smart Plant Monitoring and Watering System

This project is a hardware-based IoT system for smart agriculture. It reads plant environment data, controls a water pump automatically, logs sensor data for future machine learning work, and sends monitoring data to a Favoriot dashboard.

## Hardware

- Raspberry Pi 400
- DHT11 temperature and humidity sensor
- Soil moisture sensor analog output AO
- MCP3008 ADC for soil sensor analog-to-digital conversion
- SSD1306 OLED I2C display, 128x64
- 1-channel relay module
- DC water pump
- Favoriot IoT dashboard

## Current Behavior

- Reads temperature and humidity from DHT11.
- Reads soil moisture AO through MCP3008 channel 0.
- Converts soil reading to a moisture percentage where `0%` is very dry and `100%` is very wet.
- Classifies soil condition:
  - `< 30%`: `DRY`
  - `30%` to `70%`: `OPTIMAL`
  - `> 70%`: `WET`
- Controls an active-LOW relay on GPIO18:
  - `GPIO.LOW`: pump ON
  - `GPIO.HIGH`: pump OFF
- Shows live data on the OLED display.
- Saves readings to `plant_data.csv`.
- Sends data to Favoriot using REST API.
- Samples, logs, displays, and uploads data every 10 minutes by default.

## Favoriot Dashboard Fields

The script sends this payload under the configured `device_developer_id`:

- `temperature`
- `humidity`
- `soil_value`
- `soil_status`
- `pump_status`

## CSV Columns

`plant_data.csv` uses these columns:

- `timestamp`
- `temperature`
- `humidity`
- `soil_value`
- `soil_status`
- `pump_status`

## Setup

Install Raspberry Pi OS packages needed for GPIO, I2C, SPI, and DHT support first if your Pi does not already have them.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Enable Raspberry Pi interfaces:

```bash
sudo raspi-config
```

Enable:

- I2C for the OLED display
- SPI for MCP3008

## Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your real Favoriot values:

```bash
FAVORIOT_API_KEY=your_real_api_key
FAVORIOT_DEVICE_DEVELOPER_ID=your_device_developer_id
```

Do not commit `.env` to GitHub. It is ignored by `.gitignore`.

Useful hardware settings in `.env`:

```bash
DHT_PIN=D4
SOIL_CHANNEL=0
RELAY_PIN=18
READ_INTERVAL_SECONDS=600
SOIL_DRY_RAW=1.0
SOIL_WET_RAW=0.0
DRY_PERCENT=30
WET_PERCENT=70
```

If your DHT11 data wire is moved from GPIO4 to GPIO17, change:

```bash
DHT_PIN=D17
```

## Run

```bash
python3 full_monitor.py
```

Stop with `Ctrl+C`. The script turns the pump OFF, clears GPIO, exits the DHT sensor cleanly, and clears the OLED.

The default sampling interval is 10 minutes. To test faster during a demo, temporarily set `READ_INTERVAL_SECONDS=30` or another smaller value in `.env`.

## Project Structure

- `full_monitor.py`: Raspberry Pi hardware loop.
- `plant_monitor/logic.py`: soil percentage, classification, pump decision, and Favoriot config logic.
- `plant_monitor/app.py`: CSV writing, Favoriot payload/sending, relay output helper, OLED text formatting.
- `plant_monitor/env.py`: local `.env` loader.
- `plant_monitor/settings.py`: environment-backed runtime settings.
- `tests/`: unit tests for the non-hardware logic.

## Test

The unit tests can run on a normal computer because they avoid Raspberry Pi hardware imports.

```bash
python -m unittest discover -s tests
```
