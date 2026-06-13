# Code Explanation

This file explains how the project code works in simple terms. Use it when preparing the report, presentation, or debugging the Raspberry Pi demo.

## Big Picture

The project has two main programs:

- `full_monitor.py` runs the real monitoring loop on the Raspberry Pi.
- `streamlit_app.py` reads `plant_data.csv` and shows the dashboard.

The Raspberry Pi script is the only part that reads the sensors and controls the pump. Streamlit does not control hardware directly. It shows the latest data that was already saved by `full_monitor.py`.

```text
DHT11 + soil sensor
  -> full_monitor.py
  -> plant_data.csv
  -> streamlit_app.py
```

## Runtime Flow

When `full_monitor.py` starts, it does this:

1. Loads `.env` settings.
2. Creates `plant_data.csv` if it does not exist.
3. Loads Favoriot and Telegram configuration.
4. Loads the ML model from `MODEL_PATH`, or trains from `TRAINING_CSV_FILE`.
5. Prints startup diagnostics.
6. Sets up Raspberry Pi hardware if `SIMULATION_MODE=false`.
7. Repeats one monitoring cycle every `READ_INTERVAL_SECONDS`.

During each monitoring cycle:

1. Reads previous soil moisture from the latest CSV row.
2. Reads real sensors, or simulation values if `SIMULATION_MODE=true`.
3. Converts raw soil reading into moisture percentage.
4. Classifies soil as `DRY`, `OPTIMAL`, or `WET`.
5. Calculates `moisture_change_rate`.
6. Uses ML to predict `Dry Soon` or `Not Dry Soon`.
7. Decides pump status.
8. Detects alert conditions.
9. Sends Telegram alerts if enabled and not in cooldown.
10. Writes the reading into `plant_data.csv`.
11. Sends data to Favoriot if configured.
12. Updates the OLED display.

## Main Files

### `full_monitor.py`

This is the main Raspberry Pi program.

Important settings loaded from `.env`:

- `CSV_FILE`: where readings are saved.
- `DHT_PIN`: DHT11 data pin, normally `D4`.
- `SOIL_CHANNEL`: MCP3008 channel for soil sensor AO, normally `0`.
- `RELAY_PIN`: relay GPIO pin, normally `18`.
- `READ_INTERVAL_SECONDS`: sampling interval, default `600` seconds or 10 minutes.
- `SIMULATION_MODE`: use fake test values instead of hardware.
- `RUN_ONCE`: run one cycle only, useful for debugging.
- `ML_CONTROL_MODE`: `recommend` or `control`.
- `TRAINING_CSV_FILE`: training CSV path, usually `data/training_smart_agriculture.csv`.

Important functions:

- `simulated_sensor_values()` returns fake values for laptop testing.
- `setup_hardware()` initializes DHT11, MCP3008, OLED, relay, and GPIO.
- `read_hardware_values()` reads DHT11 and MCP3008.
- `build_reading_from_values()` creates one complete `SensorReading`.
- `run_cycle()` performs one full sensor-read, prediction, pump, notification, CSV, and OLED cycle.
- `cleanup()` turns the pump OFF and releases GPIO when the script stops.

### `plant_monitor/app.py`

This file handles shared application data and outputs.

Important parts:

- `SensorReading` stores one complete sensor record.
- `CSV_HEADER` defines all CSV columns.
- `ensure_csv_header()` creates the CSV header if needed.
- `write_csv_reading()` appends one reading to `plant_data.csv`.
- `read_latest_soil_value()` gets the previous soil value for trend calculation.
- `build_favoriot_payload()` prepares data for Favoriot.
- `send_to_favoriot()` sends REST API data if Favoriot is configured.
- `set_pump_output()` controls the active-LOW relay.
- `format_oled_lines()` creates the OLED display text.

### `plant_monitor/logic.py`

This file contains rule-based logic.

Important functions:

- `raw_to_moisture_percent()` converts MCP3008 value into `0%` to `100%`.
- `classify_soil()` returns `DRY`, `OPTIMAL`, or `WET`.
- `decide_pump_status()` turns pump ON only when soil is `DRY`.
- `decide_pump_status_with_ml()` allows early pump control only if `ML_CONTROL_MODE=control`.
- `load_favoriot_config()` reads Favoriot settings from `.env`.

Pump decision:

```text
DRY -> pump ON
WET -> pump OFF
OPTIMAL + ML Dry Soon + recommend mode -> pump OFF, warning only
OPTIMAL + ML Dry Soon + control mode -> pump ON early
```

### `plant_monitor/ml.py`

This file contains the machine learning logic.

The model is a `DecisionTreeClassifier`.

Model input features:

- `soil_value`
- `temperature`
- `humidity`
- `previous_soil_value`
- `moisture_change_rate`
- `pump_status_code`

Model output:

- `Dry Soon`
- `Not Dry Soon`

Training data priority:

1. If `MODEL_PATH` already exists, load the saved model.
2. Else, if `TRAINING_CSV_FILE` exists, train from that CSV.
3. Else, train from a small bootstrap demo dataset.

Kaggle dataset support:

- `MOI` becomes `soil_value`.
- `temp` becomes `temperature`.
- `humidity` stays `humidity`.
- `result=0` becomes `Not Dry Soon`.
- `result=1` and `result=2` become `Dry Soon`.

Real Raspberry Pi retraining:

- After collecting real readings, set `TRAINING_CSV_FILE=plant_data.csv`.
- If `dry_soon_label` is blank, the trainer uses the next CSV row to create the label.
- With 10-minute sampling, the next row means "will soil become dry in the next 10 minutes?"

### `plant_monitor/notifications.py`

This file handles risk detection and Telegram alerts.

Alert conditions:

- ML prediction is `Dry Soon`.
- Soil status is `DRY`.
- Soil status is `WET`.
- DHT11 temperature or humidity is missing.

Important functions:

- `detect_risk_events()` checks the latest reading and returns alert names.
- `format_notification_message()` creates the Telegram message text.
- `send_telegram_alerts()` sends alerts to Telegram and applies cooldown.

### `plant_monitor/debug.py`

This file creates startup diagnostics and debug reason codes.

Examples:

- `DHT_PIN`
- `MCP3008_CHANNEL`
- `RELAY_PIN`
- `CSV_PATH`
- `FAVORIOT_CONFIG`
- `TELEGRAM_CONFIG`
- `MODEL_FILE`

The output helps you quickly see whether the system is in simulation mode, whether Telegram is configured, and whether the model file exists.

### `plant_monitor/settings.py`

This file reads common `.env` settings.

Examples:

- `read_interval_seconds()`
- `debug_mode_enabled()`
- `simulation_mode_enabled()`
- `run_once_enabled()`
- `ml_control_mode()`
- `telegram_config_from_env()`

### `streamlit_app.py`

This is the dashboard.

Important point:

```text
Streamlit does not read sensors directly.
Streamlit reads plant_data.csv.
```

Dashboard features:

- Latest soil moisture, temperature, humidity, pump status, and ML prediction.
- Alert banners for risk conditions.
- Soil moisture chart.
- Temperature and humidity chart.
- Moisture change rate chart.
- Recent CSV data table.
- Debug tab with configuration status and wiring hints.

## How Telegram Alerts Work

Telegram is optional. It only works if enabled in `.env`.

Required `.env` settings:

```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
NOTIFICATION_COOLDOWN_SECONDS=1800
TELEGRAM_STATE_FILE=.telegram_state.json
```

How to get the bot token:

1. Open Telegram.
2. Search for `BotFather`.
3. Send `/newbot`.
4. Follow the instructions.
5. Copy the bot token into `TELEGRAM_BOT_TOKEN`.

How to get the chat ID:

1. Send any message to your new bot.
2. Open this URL in a browser, replacing `<TOKEN>`:

```text
https://api.telegram.org/bot<TOKEN>/getUpdates
```

3. Find `"chat":{"id":...}`.
4. Copy that number into `TELEGRAM_CHAT_ID`.

What triggers a Telegram message:

```text
Dry Soon      -> ML predicts soil may become dry soon
DRY           -> soil moisture is below 30%
WET           -> soil moisture is above 70%
DHT Missing   -> DHT11 temperature or humidity failed
```

What the message contains:

```text
Smart Plant Alert
Risk: Dry Soon
Soil: 45.0%
Temp: 32.0 C
Humidity: 55.0%
Pump: OFF
ML: Dry Soon
```

How cooldown works:

- The default cooldown is `1800` seconds, or 30 minutes.
- Cooldown is tracked per warning type.
- Example: if `Dry Soon` was sent at 10:00, another `Dry Soon` alert will not be sent until 10:30.
- A different warning type, such as `DRY`, can still be sent before the `Dry Soon` cooldown ends.
- The last sent time is saved in `.telegram_state.json`.

Telegram status values:

```text
NO_RISK                     -> no alert condition detected
TELEGRAM_SKIPPED            -> Telegram disabled or missing token/chat ID
TELEGRAM_SENT:Dry Soon      -> message sent successfully
TELEGRAM_COOLDOWN:Dry Soon  -> alert detected but blocked by cooldown
TELEGRAM_ERROR:400          -> Telegram API returned an error
```

Where Telegram status appears:

- Terminal output under `Notification:`
- `plant_data.csv` column `notification_status`
- Streamlit recent data table and debug view

Important:

```text
full_monitor.py sends Telegram messages.
streamlit_app.py only displays alert banners from plant_data.csv.
```

## Debugging Checklist

If the system does not send Telegram messages:

1. Check `.env` has `TELEGRAM_ENABLED=true`.
2. Check `TELEGRAM_BOT_TOKEN` is not empty.
3. Check `TELEGRAM_CHAT_ID` is not empty.
4. Send a message to the bot first before using `getUpdates`.
5. Check terminal `Notification:` output.
6. Check `plant_data.csv` `notification_status`.
7. Delete `.telegram_state.json` only if you want to reset cooldown during testing.

If Streamlit does not show live data:

1. Make sure `full_monitor.py` is running.
2. Make sure both scripts use the same `CSV_FILE`.
3. Refresh Streamlit or wait up to 30 seconds.
4. Check whether the CSV is stale in the Streamlit Debug tab.

If the pump does not turn ON:

1. Check soil status is actually `DRY`.
2. Remember the relay is active LOW.
3. In `recommend` mode, ML does not turn the pump ON early.
4. Use `ML_CONTROL_MODE=control` only if you want ML early watering.
5. Check relay wiring and GPIO18.
