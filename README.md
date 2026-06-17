# Raspberry Pi 400 Smart Plant Monitoring and Watering System

This project is a hardware-based IoT smart agriculture system. It reads soil moisture, temperature, and humidity, saves the readings into `plant_data.csv`, forecasts future soil moisture using SARIMAX, controls a water pump safely, shows a Streamlit dashboard, and can send Telegram/Favoriot updates.

## Main Objective

The new ML objective is:

```text
Forecast soil moisture for the next 4 hours, 6 hours, and 8 hours.
```

This is stronger than only predicting `Dry Soon / Not Dry Soon` because the dashboard can show the future soil value, not only a class label.

## System Flow

```text
DHT11 + soil sensor
  -> Raspberry Pi 400 full_monitor.py
  -> preprocessing and feature extraction
  -> SARIMAX forecast for 4h / 6h / 8h
  -> pump decision
  -> OLED display
  -> plant_data.csv
  -> Streamlit dashboard
  -> optional Telegram and Favoriot
```

`full_monitor.py` reads sensors and controls hardware. `streamlit_app.py` does not read sensors directly; it reads `plant_data.csv`, so both programs work together.

## Hardware

- Raspberry Pi 400
- DHT11 temperature and humidity sensor
- Soil moisture sensor with analog output AO
- MCP3008 ADC
- SSD1306 OLED I2C display 128x64
- 1-channel active-LOW relay module
- DC water pump
- Streamlit dashboard
- Optional Telegram bot
- Optional Favoriot IoT dashboard

## Decision Logic

The system keeps a safe threshold backup:

```text
soil_value < 30%  -> DRY -> pump ON
30% to 70%        -> OPTIMAL
soil_value > 70%  -> WET -> pump OFF
```

Forecast logic:

```text
If any forecast value at 4h, 6h, or 8h is below 30%, forecast_risk = Dry Forecast.
```

Pump safety:

```text
ML_CONTROL_MODE=recommend
Forecast dry -> show warning only, pump stays OFF unless soil is already DRY.

ML_CONTROL_MODE=control
Forecast dry + soil is OPTIMAL -> pump may turn ON early.
```

Default mode is `recommend` for safer demonstrations.

## CSV Columns

`plant_data.csv` stores every reading:

- `timestamp`
- `temperature`
- `humidity`
- `soil_value`
- `previous_soil_value`
- `moisture_change_rate`
- `vpd`
- `soil_lag_1`
- `soil_lag_2`
- `soil_lag_3`
- `soil_rolling_mean`
- `soil_rate_per_hour`
- `soil_status`
- `pump_status`
- `forecast_soil_4hr`
- `forecast_soil_6hr`
- `forecast_soil_8hr`
- `forecast_risk`
- `forecast_recommendation`
- `ml_prediction`
- `dry_soon_label`
- `notification_status`
- `debug_status`

`ml_prediction` is kept for compatibility. It now shows `Forecast Dry`, `Forecast OK`, or `Unknown`.

## Forecast Features

SARIMAX uses real timestamped `plant_data.csv` readings. The code creates:

- lag features: `soil_lag_1`, `soil_lag_2`, `soil_lag_3`
- recent rolling mean: `soil_rolling_mean`
- drying speed: `soil_rate_per_hour`
- vapour pressure deficit: `vpd`
- future targets: `target_soil_4hr`, `target_soil_6hr`, `target_soil_8hr`

Future temperature, humidity, and VPD are estimated using the recent average window:

```bash
FORECAST_RECENT_AVERAGE_HOURS=1
```

## Kaggle vs Real Data

The Kaggle smart agriculture CSV can remain in the repo as starter/classification data and report evidence. For SARIMAX forecasting, the correct training source is real timestamped Raspberry Pi data:

```text
plant_data.csv
```

Reason: SARIMAX is a time-series model. It needs readings in time order with timestamps.

## Setup

```bash
cd ~/anaconda_projects/iot/project/soil-moisture-iot
source ~/venvs/ml_env/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Raspberry Pi, enable I2C and SPI:

```bash
sudo raspi-config
```

## Important `.env` Settings

```bash
DHT_PIN=D4
SOIL_CHANNEL=0
RELAY_PIN=18
READ_INTERVAL_SECONDS=600
ML_CONTROL_MODE=recommend
DEBUG_MODE=false
SIMULATION_MODE=false
RUN_ONCE=false
DRY_PERCENT=30
WET_PERCENT=70
CSV_FILE=plant_data.csv

FORECAST_MODEL_PATH=models/soil_forecast_sarimax.joblib
FORECAST_MIN_ROWS=24
FORECAST_RECENT_AVERAGE_HOURS=1
FORECAST_HORIZONS_HOURS=4,6,8
FORECAST_DRY_PERCENT=30

STREAMLIT_REFRESH_SECONDS=10
```

## Run Commands

Test one cycle without Raspberry Pi hardware:

```bash
SIMULATION_MODE=true RUN_ONCE=true python full_monitor.py
```

Run real hardware on Raspberry Pi:

```bash
python full_monitor.py
```

Run Streamlit dashboard in another terminal:

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0
```

Open:

```text
http://<raspberry-pi-ip-address>:8501
```

## Train SARIMAX Forecast Model

After collecting enough real rows in `plant_data.csv`, run:

```bash
python -m plant_monitor.train_forecast_model
```

If there are not enough rows, the command prints `FORECAST_NOT_ENOUGH_DATA`. The monitor and dashboard will still run, but forecast values show as unavailable and pump control falls back to current soil threshold logic.

## Demo Settings

Normal collection:

```bash
READ_INTERVAL_SECONDS=600
NOTIFICATION_COOLDOWN_SECONDS=1800
STREAMLIT_REFRESH_SECONDS=10
```

Lecturer demo:

```bash
READ_INTERVAL_SECONDS=10
NOTIFICATION_COOLDOWN_SECONDS=60
STREAMLIT_REFRESH_SECONDS=10
ML_CONTROL_MODE=recommend
```

After the demo, change `READ_INTERVAL_SECONDS` back to `600`.

## Telegram Alerts

Telegram is optional. Add these to `.env`:

```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_or_group_id
NOTIFICATION_COOLDOWN_SECONDS=1800
```

Alert triggers:

- `Forecast Dry`
- `DRY`
- `WET`
- `DHT Missing`

Telegram sends the same warning type only once per cooldown period.

## Tests

```bash
python -m unittest discover -s tests
python -m compileall full_monitor.py plant_monitor tests streamlit_app.py
```
