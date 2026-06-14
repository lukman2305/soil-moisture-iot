# Student Guide

This guide combines the main explanations from our discussion into one place. Read this first if the project feels confusing.

## 1. One-Sentence Project Explanation

This project is a Raspberry Pi 400 smart irrigation system that reads soil moisture, temperature, and humidity, predicts whether the soil may become dry soon using machine learning, controls a water pump, saves readings into CSV, shows a Streamlit dashboard, and sends Telegram alerts.

## 2. What Runs Where

Use laptop, WSL, or VS Code for:

- editing code
- testing in simulation mode
- running unit tests
- checking Streamlit with sample CSV data

Use Raspberry Pi 400 for:

- real DHT11 readings
- real soil moisture readings through MCP3008
- relay and water pump control
- OLED display
- real demo

Simple rule:

```text
Laptop / WSL = test and develop
Raspberry Pi = real hardware demo
```

## 3. Main System Flow

```text
DHT11 sensor + soil moisture sensor
  -> Raspberry Pi full_monitor.py
  -> preprocessing and ML prediction
  -> pump decision
  -> OLED display
  -> plant_data.csv
  -> Streamlit dashboard
  -> optional Telegram / Favoriot
```

Important:

```text
full_monitor.py reads sensors and controls hardware.
streamlit_app.py does not read sensors directly.
streamlit_app.py reads plant_data.csv.
```

So Streamlit shows real data only when `full_monitor.py` is running on the Raspberry Pi and writing real readings into `plant_data.csv`.

## 4. What `full_monitor.py` Does

`full_monitor.py` is not only for training. It is the main program.

When it starts:

1. Loads `.env`.
2. Creates/checks `plant_data.csv`.
3. Loads Telegram and Favoriot settings.
4. Loads a saved ML model, or trains one from CSV if no model exists.
5. Starts hardware setup if `SIMULATION_MODE=false`.
6. Runs one sensor cycle every `READ_INTERVAL_SECONDS`.

During each sensor cycle:

1. Reads temperature and humidity.
2. Reads soil moisture.
3. Converts soil moisture into percentage.
4. Calculates `soil_status`.
5. Calculates `moisture_change_rate`.
6. Predicts `Dry Soon` or `Not Dry Soon`.
7. Decides pump `ON` or `OFF`.
8. Sends Telegram alert if needed.
9. Saves the row into `plant_data.csv`.
10. Updates OLED.

## 5. Model and Training Data

The model predicts:

```text
Will the soil become dry in the next 10 minutes?
```

Model inputs:

- current soil moisture
- temperature
- humidity
- previous soil moisture
- moisture change rate
- pump status

Model output:

- `Dry Soon`
- `Not Dry Soon`
- `Unknown` if important sensor data is missing

## 6. When the Model Trains

The model trains or loads when `full_monitor.py` starts.

Priority order:

| Saved model exists? | Training CSV exists? | What happens | Terminal status |
|---|---|---|---|
| Yes | Yes | Load saved model, ignore CSV | `MODEL_LOADED` |
| Yes | No | Load saved model | `MODEL_LOADED` |
| No | Yes | Train from CSV | `MODEL_TRAINED_FROM_CSV` |
| No | No | Use built-in demo data | `MODEL_BOOTSTRAP_USED` |

Training happens once at startup.

Prediction happens every sensor cycle.

```text
Training = before the loop starts
Prediction = every new sensor reading
```

## 7. Kaggle Data vs Real Data

There are two possible training sources:

```bash
TRAINING_CSV_FILE=data/training_smart_agriculture.csv
```

This uses the Kaggle smart agriculture dataset.

```bash
TRAINING_CSV_FILE=plant_data.csv
```

This uses your real Raspberry Pi collected data.

Current project idea:

```text
Kaggle data = starter training data
Real plant_data.csv = later retraining data
```

The system does not combine Kaggle and real data automatically right now. It uses the file selected by `TRAINING_CSV_FILE`, unless a saved model already exists.

## 8. Does It Retrain on Real-Time Data Automatically?

No.

The system collects real-time data into `plant_data.csv`, but it does not retrain every 10 minutes.

Correct explanation:

```text
1. Train initial model using Kaggle data.
2. Use the model to predict real-time sensor readings.
3. Save real sensor readings into plant_data.csv.
4. Later, retrain using plant_data.csv after enough real data is collected.
```

Use the word `retrain`, not `fine-tune`, because a Decision Tree is normally retrained from data.

## 9. Does It Save the Model?

`full_monitor.py` can load a saved model, but it does not automatically save the model after training.

If no saved model exists, it trains from CSV and uses that model in memory.

To manually train and save a model:

```bash
cd ~/anaconda_projects/iot/project/soil-moisture-iot
source ~/venvs/ml_env/bin/activate
python -c "from plant_monitor.ml import load_or_train_model, save_model; model=load_or_train_model(model_path=None, training_csv_path='data/training_smart_agriculture.csv'); save_model(model, 'models/dryness_model.joblib'); print(model.status_code, model.labels)"
```

After the saved model exists, `full_monitor.py` should show:

```text
ML model: MODEL_LOADED
```

## 10. How Real Sensor Data Becomes ML Features

Your real hardware directly gives:

- soil moisture
- temperature
- humidity
- pump status

The code creates extra features:

- `previous_soil_value`
- `moisture_change_rate`

Example:

| Time | Soil value | Previous soil | Moisture change |
|---|---:|---:|---:|
| 10:00 | 55% | 55% | 0% |
| 10:10 | 45% | 55% | -10% |
| 10:20 | 28% | 45% | -17% |

This helps the model learn whether soil is drying quickly.

## 11. Why Threshold Is Still Used

The threshold is used in two places.

For current soil status:

```text
soil_value < 30%  -> DRY
30% to 70%        -> OPTIMAL
soil_value > 70%  -> WET
```

For creating labels from real collected data:

```text
next soil value < 30%  -> current row label = Dry Soon
next soil value >= 30% -> current row label = Not Dry Soon
```

Important explanation:

```text
Threshold creates labels.
ML learns patterns from features.
```

So ML is not only checking whether current soil is below 30%. It can predict `Dry Soon` while current soil is still `OPTIMAL`.

## 12. Status Meanings

Main statuses:

| Status type | Values | Meaning |
|---|---|---|
| `soil_status` | `DRY`, `OPTIMAL`, `WET` | Current soil condition |
| `pump_status` | `ON`, `OFF` | Water pump state |
| `ml_prediction` | `Dry Soon`, `Not Dry Soon`, `Unknown` | ML prediction |
| `notification_status` | `NO_RISK`, `TELEGRAM_SENT`, `TELEGRAM_COOLDOWN`, `TELEGRAM_SKIPPED`, `TELEGRAM_ERROR` | Alert result |
| `debug_status` | `OK`, `MODEL_MISSING`, etc. | Startup/debug information |

Why `ml_prediction` can be `Unknown`:

```text
If temperature or humidity is missing, the model does not guess.
It returns Unknown.
```

This usually means DHT11 failed to read.

## 13. Pump Decision

Default safe mode:

```bash
ML_CONTROL_MODE=recommend
```

In recommend mode:

```text
DRY -> pump ON
WET -> pump OFF
OPTIMAL + ML Dry Soon -> pump OFF, alert only
```

Automated ML control mode:

```bash
ML_CONTROL_MODE=control
```

In control mode:

```text
DRY -> pump ON
WET -> pump OFF
OPTIMAL + ML Dry Soon -> pump ON early
```

For demo safety, use:

```bash
ML_CONTROL_MODE=recommend
```

Then say:

> The ML model gives early warning, but the pump still follows safe threshold control unless control mode is enabled.

## 14. CSV Columns

`plant_data.csv` stores every reading.

| Column | Meaning |
|---|---|
| `timestamp` | Date/time of reading |
| `temperature` | DHT11 temperature |
| `humidity` | DHT11 humidity |
| `soil_value` | Soil moisture percentage |
| `previous_soil_value` | Previous moisture reading |
| `moisture_change_rate` | Current minus previous moisture |
| `soil_status` | `DRY`, `OPTIMAL`, or `WET` |
| `pump_status` | `ON` or `OFF` |
| `ml_prediction` | `Dry Soon`, `Not Dry Soon`, or `Unknown` |
| `dry_soon_label` | Label for future retraining |
| `notification_status` | Telegram/alert status |
| `debug_status` | Debug result |

Streamlit reads this file to show the dashboard.

## 15. Streamlit Dashboard

Streamlit is the main dashboard.

It shows:

- latest soil moisture
- latest temperature
- latest humidity
- pump status
- ML prediction
- alert banners
- soil moisture chart
- temperature chart
- humidity chart
- moisture change rate chart
- recent CSV rows
- debug/system status tab

Why there is a debug tab:

```text
Hardware demos fail easily because of wiring, missing CSV, stale data, or missing Telegram config.
The debug tab helps quickly find the problem.
```

For presentation, you can call it `System Status` verbally.

## 16. OLED Display

OLED shows a short live hardware summary:

```text
SMART PLANT
Temp: 32.0 C
Humid: 55.0%
Soil: 45.0%
ML:Dry Soon P:OFF
```

If DHT11 fails:

```text
SMART PLANT
DHT Error
Soil: 45.0%
ML:Dry Soon P:OFF
```

## 17. Telegram Alert

Telegram alerts are sent by `full_monitor.py`.

Streamlit does not send Telegram messages. Streamlit only displays the status saved in `plant_data.csv`.

Telegram triggers:

```text
Dry Soon    -> ML predicts future dryness
DRY         -> soil moisture below 30%
WET         -> soil moisture above 70%
DHT Missing -> DHT11 failed
```

Example message:

```text
Smart Plant Alert
Risk: Dry Soon
Soil: 45.0%
Temp: 32.0 C
Humidity: 55.0%
Pump: OFF
ML: Dry Soon
```

Telegram settings in `.env`:

```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_personal_or_group_chat_id
NOTIFICATION_COOLDOWN_SECONDS=1800
TELEGRAM_STATE_FILE=.telegram_state.json
```

Cooldown:

```text
Same warning type can send once every 30 minutes.
Different warning types have separate cooldowns.
```

Example:

```text
10:00 Dry Soon -> sent
10:10 Dry Soon -> cooldown, not sent
10:30 Dry Soon still exists -> sent again
```

For a Telegram group, use the group chat ID. It usually starts with `-100`.

## 18. Demo Interval

Normal data collection:

```bash
READ_INTERVAL_SECONDS=600
```

This means 10 minutes.

For demo:

```bash
READ_INTERVAL_SECONDS=10
```

Recommended demo settings:

```bash
READ_INTERVAL_SECONDS=10
NOTIFICATION_COOLDOWN_SECONDS=60
ML_CONTROL_MODE=recommend
SIMULATION_MODE=false
RUN_ONCE=false
```

After demo, change back:

```bash
READ_INTERVAL_SECONDS=600
NOTIFICATION_COOLDOWN_SECONDS=1800
```

## 19. Commands to Run

Go to project:

```bash
cd ~/anaconda_projects/iot/project/soil-moisture-iot
```

Activate environment:

```bash
source ~/venvs/ml_env/bin/activate
```

Run tests:

```bash
python -m unittest discover -s tests
```

Test without hardware:

```bash
SIMULATION_MODE=true RUN_ONCE=true python full_monitor.py
```

Run real hardware on Raspberry Pi:

```bash
python full_monitor.py
```

Run Streamlit:

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0
```

Open from laptop:

```text
http://<raspberry-pi-ip-address>:8501
```

## 20. Demo Plan for Lecturer

Demo in this order:

1. Show hardware: Raspberry Pi, DHT11, soil sensor, MCP3008, OLED, relay, pump.
2. Run `full_monitor.py`.
3. Show terminal output.
4. Show OLED display.
5. Open Streamlit dashboard.
6. Show charts and recent data.
7. Create dry condition and show pump/alert.
8. Show Telegram alert if configured.
9. Explain ML vs baseline.

Three demo scenarios:

| Scenario | Expected result |
|---|---|
| Normal/optimal soil | pump OFF |
| Dry soil | pump ON |
| ML predicts Dry Soon | alert shown, pump OFF in recommend mode |

## 21. Student 4 Explanation

Student 4 is Data Processing and Intelligence.

Use this table in the report:

| Item | Baseline Rule-Based System | ML-Based System |
|---|---|---|
| Main idea | Checks current soil moisture only | Predicts future dryness |
| Inputs | Current soil moisture | Soil moisture, temperature, humidity, previous soil, trend, pump status |
| Decision | Soil below 30% means pump ON | Predicts `Dry Soon` or `Not Dry Soon` |
| Weakness | Reacts only after soil is dry | Can warn before soil becomes dry |
| Example | Soil 45% means pump OFF | Soil 45%, hot, low humidity, falling fast means `Dry Soon` |
| Benefit | Simple and reliable | Predictive and more intelligent |

Short explanation:

> The baseline system uses a fixed threshold. The ML system adds predictive intelligence by using temperature, humidity, and moisture trend to predict whether soil will become dry in the next 10 minutes.

## 22. Student 5 Explanation

Student 5 is Dashboard, Visualization, and Connectivity.

Covered parts:

- Streamlit dashboard as main dashboard.
- CSV monitoring.
- Charts.
- Alert banners.
- Debug/System Status tab.
- Telegram alerts.
- Optional Favoriot communication.

Use this sentence:

> Streamlit is used as the main monitoring dashboard because it displays real-time CSV readings, charts, alert banners, and debugging information. Favoriot is kept as optional cloud connectivity, while Telegram provides user notification when risk is detected.

## 23. Short Presentation Script

> This project is a Raspberry Pi 400 smart irrigation system. It reads temperature and humidity using DHT11, and soil moisture using an analog soil sensor through MCP3008. The system saves readings into CSV and displays them in a Streamlit dashboard. A rule-based system turns the pump ON when soil moisture is already dry. The ML model adds predictive intelligence by predicting whether the soil will become dry in the next 10 minutes using soil moisture, temperature, humidity, previous soil value, moisture trend, and pump status. Telegram alerts notify the user when the soil is dry, wet, predicted to become dry soon, or when DHT data is missing.

## 24. What to Say If Asked Why ML Is Useful

Say:

> A normal threshold system only reacts when the soil is already dry. The ML model can predict future dryness by learning patterns from soil moisture, temperature, humidity, and moisture trend. This makes the system predictive instead of only reactive.

## 25. What to Say If Asked About Kaggle Data

Say:

> Kaggle data is used as a starter dataset to train the first model before enough real sensor data is collected. During operation, the Raspberry Pi collects real data into `plant_data.csv`. Later, the model can be retrained using this real data so the predictions better match the actual plant environment.

## 26. FAQ From Common Questions

### Does the project currently have a saved model?

Yes. A saved model file is included:

```text
models/dryness_model.joblib
```

When this file exists, `full_monitor.py` loads it at startup.

Expected terminal output:

```text
ML model: MODEL_LOADED
```

If the model file is removed, the system trains from the CSV selected by `TRAINING_CSV_FILE`.

### When does the model train?

The model trains or loads when `full_monitor.py` starts.

It does not train every 10 minutes.

```text
Startup -> load/train model
Every cycle -> use model to predict
```

### Does `full_monitor.py` only train the model?

No. `full_monitor.py` runs the complete system:

```text
load/train model
read sensors
process sensor values
predict Dry Soon / Not Dry Soon
control pump
save CSV
update OLED
send Telegram/Favoriot if configured
```

### Which data is used if both Kaggle data and real data exist?

The code uses one training CSV at a time.

This setting controls it:

```bash
TRAINING_CSV_FILE=data/training_smart_agriculture.csv
```

This means Kaggle data is used.

If changed to:

```bash
TRAINING_CSV_FILE=plant_data.csv
```

then real collected data is used.

However, if `models/dryness_model.joblib` exists, the saved model is loaded first.

### Does the model retrain automatically using real-time data?

No.

The real-time sensor readings are saved into `plant_data.csv`. Later, the model can be retrained using that file.

Correct explanation:

```text
Kaggle data trains the first model.
Real-time sensor readings are used for prediction.
Real-time readings are saved into plant_data.csv.
Later, plant_data.csv can be used for retraining.
```

### Why can `ml_prediction` be `Unknown`?

`Unknown` appears when important sensor data is missing.

Example:

```text
DHT11 temperature missing
DHT11 humidity missing
```

The system does not guess. It returns:

```text
ml_prediction = Unknown
```

This is safer for hardware because missing data may mean sensor or wiring failure.

### How is `soil_status` decided?

The current soil moisture percentage is compared with thresholds:

```text
soil_value < 30%  -> DRY
30% to 70%        -> OPTIMAL
soil_value > 70%  -> WET
```

This appears in:

```text
terminal output
plant_data.csv
Streamlit Recent Data tab
Telegram/alert logic
```

### What does Telegram do?

Telegram sends alerts when risk is detected.

Alert triggers:

```text
Dry Soon
DRY
WET
DHT Missing
```

Cooldown:

```text
Same alert type sends once every 30 minutes by default.
```

Example:

```text
10:00 Dry Soon -> sent
10:10 Dry Soon -> cooldown
10:30 Dry Soon still exists -> sent again
```

### Why does Streamlit have a Debug tab?

The Debug tab helps during hardware testing.

It shows:

```text
CSV path
rows loaded
Telegram configured
Favoriot configured
model file exists
latest CSV row
wiring hints
```

For presentation, you can call it:

```text
System Status
```

### Why are temperature and humidity separate charts?

They use different units:

```text
temperature = C
humidity = %
```

Keeping them separate makes the dashboard easier to explain and avoids confusing the lecturer.

## 27. Missing Data Handling

There are two types of missing data:

```text
existing training data
real-time sensor data
```

They are handled differently.

### Existing Training Data Missing Values

Existing training data means:

```text
data/training_smart_agriculture.csv
plant_data.csv when used for retraining
```

For training data, rows with missing required ML values are removed before model training.

Code behavior:

```text
drop incomplete rows
```

Reason:

```text
The dataset has many rows, so removing incomplete rows is simpler and safer than inventing fake values.
```

Report sentence:

> For existing training data, missing or invalid rows are removed before model training. This avoids training the model using incomplete or unreliable records.

### Real-Time Sensor Missing Values

For real-time hardware readings, missing values may indicate sensor or wiring failure.

Handling:

| Missing item | Handling |
|---|---|
| DHT11 temperature/humidity | ML prediction becomes `Unknown` and alert becomes `DHT Missing` |
| First previous soil value | `moisture_change_rate` becomes `0.0` |
| Telegram token/chat ID | Telegram is skipped safely |
| Training CSV missing | Bootstrap demo data is used |
| Saved model missing | Train from CSV |

Why not fill missing real-time DHT data with average?

```text
Average filling can hide hardware failure.
It may also create fake weather conditions.
```

Example:

```text
actual hot condition: 36 C
average-filled value: 28 C
```

This could make the model predict incorrectly.

Report sentence:

> Missing real-time DHT11 readings are not filled with averages because this may hide a hardware fault and produce unreliable ML predictions. Instead, the system returns `Unknown` and triggers a `DHT Missing` alert.

## 28. Data Processing and Filtering Methods

Data processing means converting raw sensor readings into useful values.

In this project:

| Raw data | Processed value |
|---|---|
| Soil sensor analog value | Soil moisture percentage |
| Soil moisture percentage | `DRY`, `OPTIMAL`, or `WET` |
| Current and previous soil values | `moisture_change_rate` |
| Pump `ON/OFF` | Numeric ML feature |
| Temperature and humidity | ML input features |

Filtering means handling unusable data.

In this project:

| Problem | Handling |
|---|---|
| Missing DHT11 reading | Return `Unknown` and alert user |
| First row has no previous soil value | Set change rate to `0.0` |
| Training CSV row is incomplete | Drop the row |
| Telegram config missing | Skip Telegram safely |

## 29. Baseline Logic vs Intelligent Logic

Baseline logic is the simple rule-based method.

It only checks current soil moisture:

```text
soil_value < 30% -> pump ON
otherwise -> pump OFF
```

Intelligent logic is the ML prediction.

It uses:

```text
soil_value
temperature
humidity
previous_soil_value
moisture_change_rate
pump_status
```

It predicts:

```text
Dry Soon
Not Dry Soon
```

Comparison:

| Item | Baseline Logic | Intelligent Logic |
|---|---|---|
| Type | Rule-based | ML-based |
| Uses | Current soil moisture only | Soil, temperature, humidity, trend, pump |
| Output | `DRY`, `OPTIMAL`, `WET` | `Dry Soon`, `Not Dry Soon` |
| Behavior | Reactive | Predictive |
| Example | 45% soil means pump OFF | 45% soil plus hot/dry/falling trend means `Dry Soon` |

Report sentence:

> The baseline logic reacts only when the soil is already dry, while the intelligent logic predicts future dryness using environmental and trend features.

## 30. How Student 4 Requirements Are Fulfilled

Student 4 role:

```text
Data Processing and Intelligence Engineer
```

Assignment requirements and code evidence:

| Requirement | How our code fulfills it |
|---|---|
| Preprocessing and filtering | Converts raw soil value to percentage, handles missing DHT data, drops invalid training rows |
| Threshold or ML decision-making | Uses threshold classification and Decision Tree ML prediction |
| Feature extraction and evaluation | Creates `previous_soil_value`, `moisture_change_rate`, and `pump_status_code` |
| Compare intelligent logic against baseline | Code has both rule-based baseline and ML prediction; report table compares them |

Student 4 report paragraph:

> Student 4 handled the data processing and intelligence part of the system. Raw soil sensor values were converted into soil moisture percentages, and the soil condition was classified as `DRY`, `OPTIMAL`, or `WET`. Feature extraction was performed by calculating the previous soil value and moisture change rate. A threshold-based rule was used as the baseline method, while a Decision Tree model was used as the intelligent method to predict whether the soil will become dry in the next 10 minutes.

## 31. How Student 5 Requirements Are Fulfilled

Student 5 role:

```text
Dashboard, Visualization, and Connectivity Engineer
```

Assignment requirements and code evidence:

| Requirement | How our code fulfills it |
|---|---|
| Dashboard/monitoring interface | Streamlit dashboard shows live data from `plant_data.csv` |
| Visualization charts | Soil, temperature, humidity, and moisture change charts |
| Alerts and notifications | Streamlit alert banners and Telegram alerts |
| Monitoring features | Debug/System Status tab |
| Cloud/data transmission | Favoriot REST support and Telegram Bot API |

Student 5 report paragraph:

> Student 5 handled the dashboard, visualization, and connectivity part of the system. Streamlit was developed as the main dashboard to display live sensor readings, pump status, ML prediction, charts, alerts, recent data, and system status. Telegram notifications were implemented to send alerts when the soil is dry, wet, predicted to become dry soon, or when DHT11 data is missing. Favoriot REST API support is included as optional cloud data transmission.

## 32. Report-Ready Section for Student 4

You can copy this into the report:

> The data processing stage converts raw sensor readings into meaningful features. Soil moisture is converted into a percentage and classified as `DRY`, `OPTIMAL`, or `WET` using threshold logic. The system also extracts the previous soil value and moisture change rate to represent the drying trend. Missing real-time DHT11 values are handled by returning `Unknown` for ML prediction and generating a `DHT Missing` alert, while incomplete training rows are removed before model training.
>
> The baseline method uses a fixed threshold where soil moisture below 30% turns the pump ON. The intelligent method uses a Decision Tree model to predict whether the soil will become dry in the next 10 minutes using soil moisture, temperature, humidity, previous soil value, moisture change rate, and pump status. This makes the system predictive instead of only reactive.

## 33. Report-Ready Section for Student 5

You can copy this into the report:

> The system uses Streamlit as the main dashboard. The dashboard reads `plant_data.csv`, which is updated by the Raspberry Pi monitoring script. It displays the latest soil moisture, temperature, humidity, pump status, and ML prediction. It also includes separate charts for soil moisture, temperature, humidity, and moisture change rate. Alert banners are shown when risk is detected, and the Debug/System Status tab helps check CSV status, Telegram configuration, model availability, and wiring hints.
>
> Telegram notification is implemented using the Telegram Bot API. When the system detects `Dry Soon`, `DRY`, `WET`, or `DHT Missing`, it sends an alert message to the configured user or group chat. A cooldown mechanism prevents repeated alerts from being sent too frequently. Favoriot REST API support is also included for optional cloud connectivity and IoT platform integration.
