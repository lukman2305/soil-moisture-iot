# Code Explanation

This file explains the current SARIMAX forecast version of the smart plant project.

## Big Picture

There are two main programs:

- `full_monitor.py`: runs on Raspberry Pi, reads sensors, controls pump, writes CSV, sends alerts.
- `streamlit_app.py`: reads `plant_data.csv` and shows the dashboard.

They work together like this:

```text
Sensors -> full_monitor.py -> plant_data.csv -> streamlit_app.py
```

Streamlit does not control hardware directly.

## `full_monitor.py`

This is the main Raspberry Pi loop.

Startup:

1. Loads `.env`.
2. Checks/updates `plant_data.csv` header.
3. Loads Favoriot and Telegram config.
4. Loads the saved SARIMAX model from `FORECAST_MODEL_PATH`.
5. Prints diagnostics.
6. Sets up hardware if `SIMULATION_MODE=false`.

Each cycle:

1. Reads DHT11 temperature and humidity.
2. Reads soil sensor through MCP3008.
3. Converts raw soil sensor value to soil moisture percent.
4. Appends the current reading to recent history in memory.
5. Creates forecast features.
6. Uses SARIMAX to forecast 4h, 6h, and 8h soil moisture.
7. Classifies forecast risk.
8. Decides pump status.
9. Sends Telegram alert if needed.
10. Writes one row to `plant_data.csv`.
11. Sends Favoriot payload if configured.
12. Updates OLED.

Important safety behavior:

```text
If forecast model is missing, the code does not crash.
It falls back to current threshold pump logic.
```

## `plant_monitor/forecast.py`

This file contains the SARIMAX forecasting logic.

Important functions:

- `calculate_vpd()` calculates vapour pressure deficit from temperature and humidity.
- `enrich_forecast_features()` creates lag, rolling mean, rate, and VPD columns.
- `add_forecast_targets()` creates `target_soil_4hr`, `target_soil_6hr`, and `target_soil_8hr` for training.
- `recent_average_exog()` estimates future temperature/humidity/VPD using recent average.
- `train_forecast_model_from_frame()` trains SARIMAX from `plant_data.csv`.
- `forecast_soil_moisture()` produces forecast values.
- `classify_forecast_risk()` converts forecast values into `Dry Forecast`, `OK`, or `Unknown`.

Forecast output:

```text
forecast_soil_4hr
forecast_soil_6hr
forecast_soil_8hr
forecast_risk
forecast_recommendation
ml_prediction
```

## `plant_monitor/train_forecast_model.py`

This is the manual training command:

```bash
python -m plant_monitor.train_forecast_model
```

It reads:

```text
plant_data.csv
```

and saves:

```text
models/soil_forecast_sarimax.joblib
```

If there are not enough usable rows, it prints:

```text
FORECAST_NOT_ENOUGH_DATA
```

Minimum rows are controlled by:

```bash
FORECAST_MIN_ROWS=24
```

## `plant_monitor/app.py`

This file handles app output and shared reading structure.

Important parts:

- `SensorReading`: one complete reading record.
- `CSV_HEADER`: all columns saved to `plant_data.csv`.
- `ensure_csv_header()`: creates or upgrades the CSV header.
- `write_csv_reading()`: appends one row.
- `build_favoriot_payload()`: prepares the optional Favoriot data.
- `set_pump_output()`: writes active-LOW relay output.
- `format_oled_lines()`: creates OLED text.

The CSV includes both current readings and forecast fields.

## `plant_monitor/logic.py`

This file contains rule-based decisions.

Important functions:

- `raw_to_moisture_percent()`
- `classify_soil()`
- `decide_pump_status()`
- `decide_pump_status_with_forecast()`
- `load_favoriot_config()`

Pump rule:

```text
DRY -> ON
WET -> OFF
OPTIMAL + Dry Forecast + recommend -> OFF
OPTIMAL + Dry Forecast + control -> ON
```

## `plant_monitor/notifications.py`

This file handles alerts.

Alert triggers:

- `Forecast Dry`
- `DRY`
- `WET`
- `DHT Missing`

Telegram message includes:

- risk type
- soil value
- temperature
- humidity
- pump status
- forecast 4h/6h/8h
- recommendation

Cooldown is per warning type. If `Forecast Dry` sends at 10:00 and cooldown is 30 minutes, another `Forecast Dry` can send at 10:30 if the risk still exists.

## `streamlit_app.py`

This is the main dashboard.

It shows:

- current soil moisture
- forecast 4h
- forecast 6h
- forecast 8h
- forecast recommendation/risk
- pump status
- forecast chart with 30% threshold
- soil chart
- temperature chart
- humidity chart
- moisture trend chart
- recent CSV rows
- debug/system status

Streamlit auto-refresh is controlled by:

```bash
STREAMLIT_REFRESH_SECONDS=10
```

This refreshes the page display. It does not restart the monitor and does not read sensors.

## Telegram Setup

`.env`:

```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
NOTIFICATION_COOLDOWN_SECONDS=1800
```

For personal chat:

1. Message your bot first.
2. Open `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. Copy the chat id.

For group chat:

1. Add the bot to the group.
2. Send a group message.
3. Open `getUpdates`.
4. Copy the group chat id, usually starting with `-100`.

## Debugging

If forecast shows `Unknown`:

- model file may be missing
- not enough real rows collected
- DHT temperature/humidity may be missing
- CSV may be stale

If Telegram does not send:

- check `TELEGRAM_ENABLED=true`
- check bot token
- check chat ID
- check cooldown
- check terminal `notification_status`

If Streamlit does not update:

- make sure `full_monitor.py` is running
- make sure both scripts use the same `CSV_FILE`
- wait for `STREAMLIT_REFRESH_SECONDS`
- check Debug tab for stale CSV

If pump does not turn ON:

- check current `soil_status`
- remember relay is active LOW
- in `recommend` mode, forecast does not turn pump ON early
- use `ML_CONTROL_MODE=control` only for early automatic watering
