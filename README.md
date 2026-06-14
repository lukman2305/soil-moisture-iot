# Raspberry Pi 400 Smart Plant Monitoring and Watering System

This project is a hardware-based IoT system for smart agriculture. It reads plant environment data, predicts whether soil will become dry in the next 10 minutes, controls a water pump automatically, logs sensor data for future machine learning work, and shows monitoring data in a Streamlit dashboard. Favoriot sending remains optional for assignment compatibility.

## Start Here

If the project feels confusing, read this first:

```text
STUDENT_GUIDE.md
```

It combines the main explanation, model/training flow, status meanings, Telegram alerts, Streamlit dashboard, demo plan, and Student 4/Student 5 report points.

## Simple Project Explanation

This project is a smart plant watering system. The Raspberry Pi 400 reads the plant's environment using three main sensor values:

- soil moisture
- temperature
- humidity

A normal irrigation system only checks whether the soil is dry right now. If the soil is already dry, it turns on the pump. This project is stronger because it also uses machine learning to predict whether the soil is likely to become dry soon.

In simple words:

```text
Normal system:
Soil is dry now -> turn pump ON

Our system:
Soil is not dry yet, but temperature is high, humidity is low, and moisture is dropping -> predict Dry Soon
```

The goal is to water the plant before plant stress happens, instead of waiting until the soil is already too dry.

## Whole System Flow

```text
Sensors
  -> Raspberry Pi 400
  -> clean and process readings
  -> calculate soil condition and moisture trend
  -> machine learning predicts Dry Soon or Not Dry Soon
  -> pump decision is made
  -> OLED display updates
  -> CSV file saves data
  -> Streamlit dashboard shows charts and alerts
  -> optional Telegram/Favoriot notification is sent
```

## What Each Part Does

- **DHT11 sensor** reads temperature and humidity.
- **Soil moisture sensor** reads how wet or dry the soil is.
- **MCP3008 ADC** converts the soil sensor's analog value into a digital value the Raspberry Pi can read.
- **Raspberry Pi 400** runs the Python program, processes readings, predicts dryness, controls the pump, and saves data.
- **Relay module** switches the water pump ON or OFF.
- **OLED display** shows the latest plant status beside the hardware.
- **Streamlit dashboard** shows live status, charts, recent readings, alerts, and a debug tab.
- **Machine learning model** predicts whether the soil will become dry in the next 10 minutes.
- **Telegram notification** can send warnings to a phone when risk is detected.
- **Favoriot** is optional and can still receive IoT data if required for the assignment.

## Main Decision Logic

The system still keeps a safe rule-based backup:

```text
If soil is DRY -> pump ON
If soil is WET -> pump OFF
```

Machine learning adds predictive behavior:

```text
If soil is OPTIMAL but ML predicts Dry Soon -> warn user
If ML_CONTROL_MODE=control -> pump can turn ON early
If ML_CONTROL_MODE=recommend -> show recommendation only
```

The default setting is safe:

```text
ML_CONTROL_MODE=recommend
```

This means ML will warn or recommend, but it will not control the pump early unless the user enables control mode.

## Demo Explanation

For presentation, explain it like this:

> This project monitors soil moisture, temperature, and humidity using Raspberry Pi 400. A threshold system controls the pump when the soil is already dry. On top of that, a machine learning model predicts whether the soil will become dry in the next 10 minutes using the current moisture, previous moisture, moisture change rate, temperature, humidity, and pump status. The result is shown on an OLED display and a Streamlit dashboard. If risk is detected, the system can show alerts and optionally send Telegram notifications.

For the full student-friendly guide, read:

```text
STUDENT_GUIDE.md
```

For a file-by-file code explanation and Telegram troubleshooting guide, read:

```text
CODE_EXPLANATION.md
```

## Hardware

- Raspberry Pi 400
- DHT11 temperature and humidity sensor
- Soil moisture sensor analog output AO
- MCP3008 ADC for soil sensor analog-to-digital conversion
- SSD1306 OLED I2C display, 128x64
- 1-channel relay module
- DC water pump
- Streamlit local dashboard
- Optional Favoriot IoT dashboard
- Optional Telegram notification bot

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
- Predicts `Dry Soon` or `Not Dry Soon` using a Decision Tree model.
- Shows risk notifications on Streamlit, OLED, and optional Telegram.
- Supports simulation and one-cycle debug modes for testing without hardware.

## Favoriot Dashboard Fields

Favoriot is optional. When configured, the script sends this payload under the configured `device_developer_id`:

- `temperature`
- `humidity`
- `soil_value`
- `soil_status`
- `pump_status`
- `ml_prediction`
- `notification_status`

## CSV Columns

`plant_data.csv` uses these columns:

- `timestamp`
- `temperature`
- `humidity`
- `soil_value`
- `previous_soil_value`
- `moisture_change_rate`
- `soil_status`
- `pump_status`
- `ml_prediction`
- `dry_soon_label`
- `notification_status`
- `debug_status`

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
ML_CONTROL_MODE=recommend
DEBUG_MODE=false
SIMULATION_MODE=false
RUN_ONCE=false
SOIL_DRY_RAW=1.0
SOIL_WET_RAW=0.0
DRY_PERCENT=30
WET_PERCENT=70
TELEGRAM_ENABLED=false
NOTIFICATION_COOLDOWN_SECONDS=1800
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

Run one debug cycle without Raspberry Pi hardware:

```bash
SIMULATION_MODE=true RUN_ONCE=true python3 full_monitor.py
```

Run the Streamlit dashboard:

```bash
streamlit run streamlit_app.py
```

## Machine Learning

The model predicts:

```text
Will soil become dry in the next 10 minutes?
```

Inputs:

- current soil moisture
- temperature
- humidity
- previous soil moisture
- moisture change rate
- pump status

Output:

- `Dry Soon`
- `Not Dry Soon`

The first training source is the Kaggle smart agriculture CSV you uploaded locally:

```text
data/training_smart_agriculture.csv
```

The code now supports the raw Kaggle columns:

```text
crop ID,soil_type,Seedling Stage,MOI,temp,humidity,result
```

For this project, the Kaggle columns are converted like this:

- `MOI` -> `soil_value`
- `temp` -> `temperature`
- `humidity` -> `humidity`
- `result=0` -> `Not Dry Soon`
- `result=1` or `result=2` -> `Dry Soon`

Because the Kaggle file is not your real Raspberry Pi time series, `previous_soil_value` and `moisture_change_rate` are estimated from the previous row within the same crop, soil type, and seedling stage group. This makes Kaggle useful as a starter dataset, but your own `plant_data.csv` is still the stronger final dataset.

The canonical training format is also supported:

```text
soil_value,temperature,humidity,previous_soil_value,moisture_change_rate,pump_status,dry_soon_label
```

After collecting real sensor data for some time, you can retrain from your own CSV by changing `.env`:

```bash
TRAINING_CSV_FILE=plant_data.csv
```

If `dry_soon_label` is blank in real data, the trainer labels each row using the next sensor row. Since the default sampling time is 10 minutes, the next row means "soil condition in the next 10 minutes." If the next soil value is below `30%`, the label becomes `Dry Soon`; otherwise it becomes `Not Dry Soon`.

For safety, `ML_CONTROL_MODE=recommend` is the default. Set `ML_CONTROL_MODE=control` only when you want the ML prediction to turn the pump ON early. If a saved model file already exists and you want to force retraining, remove `models/dryness_model.joblib` or set `MODEL_PATH` to a new file name.

## Notifications and Debug

Telegram settings are optional and must stay in `.env`:

```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
NOTIFICATION_COOLDOWN_SECONDS=1800
```

Telegram sends at most one repeated warning per risk type every 30 minutes.

Telegram alerts are sent by `full_monitor.py`, not by the Streamlit dashboard. Streamlit only shows the latest alert status from `plant_data.csv`.

Telegram alert triggers:

- `Dry Soon`: the ML model predicts future dryness.
- `DRY`: soil moisture is below the dry threshold.
- `WET`: soil moisture is above the wet threshold.
- `DHT Missing`: temperature or humidity failed to read.

Telegram status is saved into the `notification_status` CSV column. Common values are:

- `NO_RISK`
- `TELEGRAM_SKIPPED`
- `TELEGRAM_SENT:Dry Soon`
- `TELEGRAM_COOLDOWN:Dry Soon`
- `TELEGRAM_ERROR:<status_code>`

The Streamlit Debug tab shows CSV status, model status, configuration status, and wiring hints for DHT11, MCP3008, relay, I2C, and SPI.

## Project Structure

- `full_monitor.py`: Raspberry Pi hardware loop.
- `plant_monitor/logic.py`: soil percentage, classification, pump decision, and Favoriot config logic.
- `plant_monitor/app.py`: CSV writing, Favoriot payload/sending, relay output helper, OLED text formatting.
- `plant_monitor/env.py`: local `.env` loader.
- `plant_monitor/ml.py`: Decision Tree training and dry-soon prediction helpers.
- `plant_monitor/notifications.py`: risk detection and Telegram alerts.
- `plant_monitor/debug.py`: startup diagnostics and reason-code logging.
- `plant_monitor/settings.py`: environment-backed runtime settings.
- `streamlit_app.py`: local monitoring dashboard.
- `tests/`: unit tests for the non-hardware logic.

## Test

The unit tests can run on a normal computer because they avoid Raspberry Pi hardware imports.

```bash
python -m unittest discover -s tests
```
