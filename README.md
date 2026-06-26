# Raspberry Pi 400 Smart Plant Monitoring and Watering System

This project is a hardware-based IoT smart agriculture system. It reads soil moisture, temperature, and humidity, saves the readings into `plant_data.csv`, forecasts future soil moisture using SARIMAX, controls a water pump with a timed relay, shows a Streamlit dashboard with login, and can send Telegram/Favoriot updates.

## Main Objective

```text
Forecast soil moisture for the next 4 hours, 6 hours, and 8 hours.
```

This is stronger than only predicting `Dry Soon / Not Dry Soon` because the dashboard can show the future soil value, not only a class label.

## System Flow

```text
DHT11 + soil sensor (10-sample smoothed average)
  -> Raspberry Pi 400 full_monitor.py
  -> preprocessing and feature extraction
  -> ARIMA(1,1,0) forecast for 4h / 6h / 8h (tracks rates of change)
  -> pump decision (timed: 10s for DRY, 3s for forecast DRY)
  -> OLED display
  -> plant_data.csv / sim_data.csv / demo_data.csv
  -> Streamlit dashboard (login required)
  -> optional Telegram and Favoriot
```

`full_monitor.py` reads sensors and controls hardware. `streamlit_app.py` does not read sensors directly; it reads the CSV file, so both programs work together.

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
soil_value < 30%  -> DRY -> pump ON for PUMP_DURATION_SECONDS (default 10s)
30% to 70%        -> OPTIMAL
soil_value > 70%  -> WET -> pump OFF
```

Forecast logic:

```text
If 4h forecast value is below 30% -> forecast_risk = Dry Forecast
-> pump ON for PUMP_FORECAST_DURATION_SECONDS (default 3s)
```

Pump safety:

```text
ML_CONTROL_MODE=recommend
Forecast dry -> show warning only, pump stays OFF unless soil is already DRY.

ML_CONTROL_MODE=control
Forecast dry + soil is OPTIMAL -> pump may turn ON early (3 seconds).
```

Default mode is `recommend` for safer demonstrations.

## Soil Sensor Smoothing

The soil sensor takes **10 samples every 50ms** and averages them instead of using a single raw reading. This removes electrical noise and gives a more stable moisture percentage.

## Run Modes

| Mode | Purpose | Data saved to | Dashboard reads |
|---|---|---|---|
| **Real hardware (normal)** | Production / data collection | `plant_data.csv` | `plant_data.csv` |
| **Real hardware (demo)** | Manipulate sensors for presentation | `demo_data.csv` | `demo_data.csv` |
| **Simulation** | Test without hardware (Dynamic environment simulation) | `sim_data.csv` | `sim_data.csv` |

`plant_data.csv` and `indoor_data.csv` are the only files used for SARIMAX training. Simulation and demo data never pollute the training dataset. When starting Simulation mode, the historical data is automatically cloned to `sim_data.csv` so the dashboard charts are instantly populated.

### Simulation Mode Dynamics
The system uses an advanced dynamic simulation engine to mimic a real environment:
- **Environment:** Temperature and humidity fluctuate on a natural sine-wave curve with simulated sensor noise.
- **Soil Drying:** Soil moisture decays slightly every cycle to simulate a drying plant.
- **Virtual Watering:** When soil drops below the `DRY_PERCENT` threshold, the virtual pump kicks on and instantly spikes moisture back to 80% to mimic a watering event.


### .env Settings Per Mode

**Real hardware — normal data collection:**
```bash
SIMULATION_MODE=false
DEMO_MODE=false
SAVE_DATA_TO_CSV=true
READ_INTERVAL_SECONDS=600
```

**Real hardware — demo / presentation (fast, manipulate sensors freely):**
```bash
SIMULATION_MODE=false
DEMO_MODE=true
SAVE_DATA_TO_CSV=true
READ_INTERVAL_SECONDS=5
NOTIFICATION_COOLDOWN_SECONDS=10
STREAMLIT_REFRESH_SECONDS=1
```

**Simulation — test without Raspberry Pi:**
```bash
SIMULATION_MODE=true
DEMO_MODE=false
SAVE_DATA_TO_CSV=true
READ_INTERVAL_SECONDS=5
SIM_SOIL_VALUE=20
SIM_TEMPERATURE=32
SIM_HUMIDITY=55
```

**Quick output check — no data saved at all:**
```bash
SAVE_DATA_TO_CSV=false
```

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

### Dashboard Login Setup

```bash
python generate_passwords.py
```

This creates `auth_config.yaml` with hashed passwords. Required before running Streamlit.

## Important `.env` Settings

```bash
DHT_PIN=D4
SOIL_CHANNEL=0
RELAY_PIN=18
READ_INTERVAL_SECONDS=600
ML_CONTROL_MODE=recommend
DEBUG_MODE=false
SIMULATION_MODE=false
DEMO_MODE=false
RUN_ONCE=false
SAVE_DATA_TO_CSV=true
DRY_PERCENT=30
WET_PERCENT=70

# Pump timer
PUMP_DURATION_SECONDS=10
PUMP_FORECAST_DURATION_SECONDS=3

FORECAST_MODEL_PATH=models/soil_forecast_sarimax.joblib
FORECAST_MIN_ROWS=24
FORECAST_RECENT_AVERAGE_HOURS=1
FORECAST_HORIZONS_HOURS=4,6,8
FORECAST_DRY_PERCENT=30

STREAMLIT_REFRESH_SECONDS=10
```

## Run Commands

Real hardware on Raspberry Pi (normal):

```bash
python full_monitor.py
```

Real hardware demo (manipulate sensors freely, data saved separately):

```bash
# Set DEMO_MODE=true in .env, then:
python full_monitor.py
```

Simulation (no Raspberry Pi needed):

```bash
SIMULATION_MODE=true python full_monitor.py
```

Test one cycle only:

```bash
SIMULATION_MODE=true RUN_ONCE=true python full_monitor.py
```

Run Streamlit dashboard in another terminal:

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0
```

> [!TIP]
> **Live Demo Mode**: Set `READ_INTERVAL_SECONDS=5` and `STREAMLIT_REFRESH_SECONDS=1` in your `.env` for fast updates. Use the **⏸️ Pause Live Updates** checkbox in the sidebar to freeze the dashboard so you can zoom in on charts.

Open:

```text
http://<raspberry-pi-ip-address>:8501
```

## Train SARIMAX Forecast Model

After collecting enough real rows in `plant_data.csv` (minimum 24), run:

```bash
python -m plant_monitor.train_forecast_model
```

Training sources are set in `.env`:

```bash
TRAINING_CSV_FILES=plant_data.csv,indoor_data.csv
```

If there are not enough rows, the command prints `FORECAST_NOT_ENOUGH_DATA`. The monitor and dashboard will still run, but forecast values show as unavailable.

## CSV Columns

`plant_data.csv` stores every reading:

- `timestamp`, `temperature`, `humidity`
- `soil_value`, `previous_soil_value`, `moisture_change_rate`
- `vpd`, `soil_lag_1`, `soil_lag_2`, `soil_lag_3`
- `soil_rolling_mean`, `soil_rate_per_hour`
- `soil_status`, `pump_status`
- `forecast_soil_4hr`, `forecast_soil_6hr`, `forecast_soil_8hr`
- `forecast_risk`, `forecast_recommendation`
- `ml_prediction`, `dry_soon_label`
- `notification_status`, `debug_status`

## Telegram Alerts

Telegram is optional. Add these to `.env`:

```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_or_group_id
NOTIFICATION_COOLDOWN_SECONDS=1800
```

Alert triggers: `Forecast Dry`, `DRY`, `WET`, `DHT Missing`

## Tests

```bash
python -m unittest discover -s tests
python -m compileall full_monitor.py plant_monitor tests streamlit_app.py
```
