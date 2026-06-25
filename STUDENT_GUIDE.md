# Student Guide

Read this when the project feels confusing. It explains the system in report and presentation language.

## One-Sentence Explanation

This project is a Raspberry Pi 400 smart irrigation system that monitors soil moisture, temperature, and humidity, forecasts future soil moisture at 4h, 6h, and 8h using SARIMAX, shows the data in Streamlit, and sends alerts when the plant may need attention.

## What Runs Where

Laptop / WSL / VS Code:

- edit code
- run unit tests
- run simulation mode
- view Streamlit using CSV data

Raspberry Pi:

- read DHT11
- read soil sensor through MCP3008
- control relay and pump
- update OLED
- collect real `plant_data.csv`

Important:

```text
full_monitor.py writes data.
streamlit_app.py reads data.
```

So yes, they work together. While `full_monitor.py` writes new rows to `plant_data.csv`, Streamlit auto-refreshes and rereads the file.

## New ML Objective

Old idea:

```text
Will soil become dry in the next 10 minutes?
```

New stronger idea:

```text
Forecast soil moisture after 4 hours, 6 hours, and 8 hours.
```

This is better because the dashboard can show expected future soil moisture values, not just `Dry Soon` or `Not Dry Soon`.

## Why SARIMAX

SARIMAX is suitable because:

- soil moisture is time-series data
- it works with small datasets better than LSTM
- it is lighter for Raspberry Pi
- it can use extra features like temperature, humidity, and VPD

LSTM usually needs more data and more computing power.

## Main Data Flow

```text
Sensors
  -> raw readings
  -> preprocessing
  -> feature extraction
  -> SARIMAX forecast
  -> pump decision
  -> CSV + OLED + Streamlit + Telegram
```

## Data Processing

The code processes data like this:

| Raw / input data | Processed result |
|---|---|
| Soil analog value | Soil moisture percentage |
| Soil percentage | `DRY`, `OPTIMAL`, `WET` |
| Current and previous soil values | `moisture_change_rate` |
| Temperature and humidity | VPD |
| Past soil rows | lag features |
| Recent soil rows | rolling mean |
| Timestamp difference | rate of change per hour |

## Forecast Features

The forecasting code creates:

| Feature | Meaning |
|---|---|
| `vpd` | Vapour pressure deficit, shows drying pressure from temperature and humidity |
| `soil_lag_1` | Previous soil reading |
| `soil_lag_2` | Two readings ago |
| `soil_lag_3` | Three readings ago |
| `soil_rolling_mean` | Recent average soil moisture |
| `soil_rate_per_hour` | How fast soil is drying or getting wetter |
| `target_soil_4hr` | Soil moisture 4 hours later for training |
| `target_soil_6hr` | Soil moisture 6 hours later for training |
| `target_soil_8hr` | Soil moisture 8 hours later for training |

## Recent Average Explained

For future temperature and humidity, the system does not know the real future weather. So it uses the recent average.

Example:

```text
FORECAST_RECENT_AVERAGE_HOURS=1
```

If the latest time is 2:00 PM, the code averages temperature, humidity, and VPD from about 1:00 PM to 2:00 PM. This becomes the future estimate for SARIMAX.

Why this is reasonable:

- it is simple to explain
- it works without a weather API
- it avoids guessing random future values
- it is suitable for a small IoT prototype

Limitation:

```text
If weather changes suddenly, the forecast may be less accurate.
```

Report sentence:

> Future environmental features were estimated using recent averages because the system does not have access to future temperature and humidity. This provides a simple and stable assumption for short-term forecasting.

## What If Soil Dries Faster or Slower Than Expected?

If soil becomes dry very fast:

- new sensor readings will show a stronger negative `soil_rate_per_hour`
- the next forecast becomes lower
- Streamlit can show `Dry Forecast`
- Telegram can send `Forecast Dry`

If soil dries very slowly:

- rate of change becomes small
- rolling mean stays stable
- forecasts remain above the dry threshold
- system recommends no early watering

Important:

```text
The forecast updates every new sensor cycle.
```

The model does not make one permanent prediction. It keeps updating as new real readings arrive.

## Baseline vs Intelligent Logic

| Item | Baseline Rule | Intelligent Forecast |
|---|---|---|
| Main idea | Check current soil only | Forecast future soil |
| Data used | Current `soil_value` | Soil, temperature, humidity, VPD, lags, rolling mean, rate |
| Output | `DRY`, `OPTIMAL`, `WET` | Forecast values at 4h, 6h, 8h |
| Behavior | Reactive | Predictive |
| Example | Soil 45% means pump OFF | Soil 45% but forecast 8h is 25%, so warn early |

Report sentence:

> The baseline system reacts only when soil moisture is already below the dry threshold. The intelligent SARIMAX logic forecasts future soil moisture using time-series and environmental features, allowing the system to warn before the plant reaches dry condition.

## Pump Decision

Current safety rule:

```text
DRY -> pump ON
WET -> pump OFF
```

Forecast rule:

```text
Any forecast value below 30% -> Dry Forecast
```

Recommend mode:

```text
ML_CONTROL_MODE=recommend
Dry Forecast -> show warning only
```

Control mode:

```text
ML_CONTROL_MODE=control
Dry Forecast + OPTIMAL soil -> pump may turn ON early
```

Use `recommend` for lecturer demo unless you want early automatic watering.

## Status Meanings

| Column | Values | Meaning |
|---|---|---|
| `soil_status` | `DRY`, `OPTIMAL`, `WET` | Current soil condition |
| `pump_status` | `ON`, `OFF` | Pump state |
| `forecast_risk` | `Dry Forecast`, `OK`, `Unknown` | Future dryness risk |
| `forecast_recommendation` | sentence text | Human-readable advice |
| `ml_prediction` | `Forecast Dry`, `Forecast OK`, `Unknown` | Compatibility label for dashboard/alerts |
| `notification_status` | Telegram status | Whether alert was sent/skipped/cooldown |
| `debug_status` | reason code | Model/data/hardware debug result |

## Missing Data Handling

Existing training data:

```text
Rows with missing required model values are removed before training.
```

Real-time sensor data:

```text
Missing DHT11 temperature/humidity is not filled with an average.
```

Reason:

```text
Average filling can hide hardware failure and create fake weather data.
```

Instead, the system shows:

- `DHT Missing`
- `forecast_risk = Unknown` if forecast cannot be trusted
- threshold pump fallback

Report sentence:

> Missing real-time DHT11 readings are not filled using averages because this may hide wiring or sensor failure. The system reports the issue and falls back to safer threshold-based behavior.

## Training Data

SARIMAX should train on:

```text
plant_data.csv
```

because it has real timestamps and real sensor readings.

The Kaggle dataset can still be mentioned as starter/reference data, but it is not the main SARIMAX training source unless it has usable timestamps.

## When the Model Trains

Manual training command:

```bash
python -m plant_monitor.train_forecast_model
```

The monitor does not retrain every 10 minutes. It loads the saved model:

```text
models/soil_forecast_sarimax.joblib
```

If no model exists:

- dashboard still runs
- monitor still logs data
- pump uses threshold control
- debug shows model/data unavailable

## Retraining After More Real Data

If you collect 10 days of real data and train, then collect another 10 days, retraining should use the whole CSV:

```text
first 10 days + second 10 days = entire 20 days
```

This is better because SARIMAX learns from the full time-series history.

## Streamlit Dashboard

Streamlit shows:

- current soil moisture
- forecast soil moisture at 4h
- forecast soil moisture at 6h
- forecast soil moisture at 8h
- forecast recommendation
- pump status
- forecast chart with 30% dry threshold line
- soil moisture chart
- temperature chart
- humidity chart
- moisture trend chart
- recent CSV rows
- debug/system status

The Debug tab exists because hardware demos often fail due to wiring, stale CSV, missing model, or missing Telegram config.

## OLED Display

OLED shows a compact live status:

```text
SMART PLANT
Temp: 32.0 C
Humid: 55.0%
Soil: 45.0%
F4:40.0 F8:28.0 P:OFF
```

If forecast is unavailable, it falls back to the ML/status line.

## Telegram Alerts

Telegram is sent by `full_monitor.py`, not Streamlit.

Triggers:

- `Forecast Dry`
- `DRY`
- `WET`
- `DHT Missing`

Cooldown example:

```text
10:00 Forecast Dry -> sent
10:10 Forecast Dry -> cooldown
10:30 Forecast Dry -> sent again if risk still exists
```

For a group, add the bot to the group and use the group chat ID, usually starting with `-100`.

## Pump Timer

The pump does not run indefinitely. It runs for a fixed number of seconds then turns off automatically:

| Trigger | Duration | Reason |
|---|---|---|
| Current soil DRY (`< 30%`) | `PUMP_DURATION_SECONDS` (default 10s) | Immediate watering |
| 4h Forecast DRY | `PUMP_FORECAST_DURATION_SECONDS` (default 3s) | Preventive early watering |

Report sentence:

> The pump uses a timed relay to prevent over-watering. When triggered by current dry soil, the pump runs for 10 seconds. When triggered by a dry forecast, it runs for 3 seconds as a preventive measure.

## Soil Sensor Smoothing

Instead of reading one raw value from the soil sensor, the system reads **10 samples with 50ms delay** between each sample and takes the average. This is called an **averaging/smoothing filter** and reduces electrical noise.

```python
def read_soil_smoothed(soil_sensor, num_samples=10, delay=0.05):
    samples = [soil_sensor.value for _ in range(num_samples)]
    return sum(samples) / len(samples)
```

## Run Modes and Data Separation

The system has three run modes. Each mode saves to a different CSV file so the real training data is never polluted:

| Mode | `.env` setting | Saves to | Dashboard reads |
|---|---|---|---|
| Real hardware (normal) | `SIMULATION_MODE=false`, `DEMO_MODE=false` | `plant_data.csv` | `plant_data.csv` |
| Real hardware (demo) | `DEMO_MODE=true` | `demo_data.csv` | `demo_data.csv` |
| Simulation | `SIMULATION_MODE=true` | `sim_data.csv` | `sim_data.csv` |

Only `plant_data.csv` and `indoor_data.csv` are used for SARIMAX training.

### What to Set in `.env` Per Mode

**Normal data collection (Raspberry Pi running 24/7):**
```bash
SIMULATION_MODE=false
DEMO_MODE=false
SAVE_DATA_TO_CSV=true
READ_INTERVAL_SECONDS=600
```

**Real hardware demo (manipulate sensors freely during presentation):**
```bash
SIMULATION_MODE=false
DEMO_MODE=true
SAVE_DATA_TO_CSV=true
READ_INTERVAL_SECONDS=5
NOTIFICATION_COOLDOWN_SECONDS=10
STREAMLIT_REFRESH_SECONDS=1
```

**Simulation (no Raspberry Pi, test on laptop):**
```bash
SIMULATION_MODE=true
DEMO_MODE=false
SAVE_DATA_TO_CSV=true
READ_INTERVAL_SECONDS=5
SIM_SOIL_VALUE=20
```

**Quick output check only (nothing saved):**
```bash
SAVE_DATA_TO_CSV=false
```

## Dashboard Login

The Streamlit dashboard requires a username and password. Run this once to create credentials:

```bash
python generate_passwords.py
```

This creates `auth_config.yaml`. Share this file manually with teammates — it is not uploaded to GitHub for security.

## Demo Commands

Real hardware demo (set `DEMO_MODE=true` in `.env` first):

```bash
python full_monitor.py
```

Simulation:

```bash
SIMULATION_MODE=true python full_monitor.py
```

Streamlit:

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0
```

Train forecast model after enough rows:

```bash
python -m plant_monitor.train_forecast_model
```

## Student 4: Data Processing and Intelligence

Student 4 requirements:

| Requirement | How the code fulfills it |
|---|---|
| Preprocessing | Converts raw soil sensor data to percentage using 10-sample averaging filter |
| Filtering | Handles missing DHT and drops incomplete training rows |
| Feature extraction | VPD, lags, rolling mean, rate per hour |
| Intelligent logic | SARIMAX forecasts 4h/6h/8h soil moisture |
| Baseline comparison | Threshold logic is compared with forecast logic |

Report paragraph:

> Student 4 handled the data processing and intelligence component. The system converts raw soil readings into moisture percentage using a 10-sample averaging filter to reduce noise, classifies soil condition using thresholds, and extracts forecasting features such as VPD, lag values, rolling mean, and soil moisture rate of change per hour. A threshold-based baseline is used for current soil control, while SARIMAX provides intelligent forecasting for future soil moisture at 4h, 6h, and 8h.

## Student 5: Dashboard, Visualization, and Connectivity

Student 5 requirements:

| Requirement | How the code fulfills it |
|---|---|
| Dashboard | Streamlit main dashboard with login authentication |
| Visualization | Soil, temperature, humidity, trend, and forecast charts |
| Monitoring | Recent CSV table and Debug/System Status tab |
| Alerts | Streamlit banners and Telegram alerts |
| Cloud/data transmission | Optional Favoriot REST payload |

Report paragraph:

> Student 5 handled dashboard, visualization, and connectivity. Streamlit is used as the main dashboard with login authentication to display current readings, 4h/6h/8h soil forecasts, pump status, alert banners, charts, recent CSV data, and debug information. Telegram notifications send alerts for forecast dryness, dry soil, wet soil, and DHT sensor failure. Favoriot remains optional for cloud visualization and IoT platform integration.

## Short Presentation Script

> This project is a Raspberry Pi 400 smart irrigation system. It reads temperature and humidity using DHT11 and soil moisture using an analog soil sensor through MCP3008, averaging 10 samples per reading for stability. The system logs readings into CSV and displays them in a Streamlit dashboard protected by a login screen. The baseline logic turns the pump ON for 10 seconds when current soil moisture is below 30%. The intelligent part uses SARIMAX to forecast soil moisture after 4, 6, and 8 hours using lag features, rolling average, drying rate, temperature, humidity, and VPD. If future soil moisture is predicted to fall below 30%, the system activates the pump for 3 seconds as a preventive measure and sends a Telegram alert.

