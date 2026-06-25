import os
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from plant_monitor.db import init_db, write_db_reading

from plant_monitor.app import (
    SensorReading,
    ensure_csv_header,
    format_oled_lines,
    send_to_favoriot,
    set_pump_output,
    write_csv_reading,
)
from plant_monitor.debug import build_startup_diagnostics, debug_status_from_diagnostics, log_event
from plant_monitor.env import load_env_file
from plant_monitor.logic import (
    classify_soil,
    decide_pump_status_with_forecast,
    load_favoriot_config,
    raw_to_moisture_percent,
)
from plant_monitor.forecast import (
    FORECAST_MODEL_MISSING,
    FORECAST_NOT_ENOUGH_DATA,
    append_current_reading,
    enrich_forecast_features,
    forecast_soil_moisture,
    load_forecast_model,
    parse_forecast_horizons,
    load_forecast_history,
)
from plant_monitor.ml import calculate_moisture_change_rate
from plant_monitor.notifications import detect_risk_events, send_telegram_alerts
from plant_monitor.settings import (
    debug_mode_enabled,
    ml_control_mode,
    demo_mode_enabled,
    pump_duration_seconds,
    pump_forecast_duration_seconds,
    read_interval_seconds,
    run_once_enabled,
    save_data_enabled,
    simulation_mode_enabled,
    telegram_config_from_env,
)


BASE_DIR = Path(__file__).resolve().parent
load_env_file(BASE_DIR / ".env")

RELAY_PIN = int(os.getenv("RELAY_PIN", "16"))
SOIL_CHANNEL = int(os.getenv("SOIL_CHANNEL", "5"))
DHT_PIN = os.getenv("DHT_PIN", "D4").upper()
READ_INTERVAL_SECONDS = read_interval_seconds()
ML_CONTROL_MODE = ml_control_mode()
DEBUG_MODE = debug_mode_enabled()
SIMULATION_MODE = simulation_mode_enabled()
DEMO_MODE = demo_mode_enabled()
RUN_ONCE = run_once_enabled()
SAVE_DATA = save_data_enabled()

# Route CSV to a separate file during simulation or demo so plant_data.csv stays clean
if SIMULATION_MODE:
    _default_csv = "sim_data.csv"
elif DEMO_MODE:
    _default_csv = "demo_data.csv"
else:
    _default_csv = "plant_data.csv"
CSV_FILE = Path(os.getenv("CSV_FILE", str(BASE_DIR / _default_csv)))
DB_FILE = Path(os.getenv("DB_FILE", str(BASE_DIR / "sensor_data.db")))
PUMP_DURATION_SECONDS = pump_duration_seconds()
PUMP_FORECAST_DURATION_SECONDS = pump_forecast_duration_seconds()

FORECAST_MODEL_PATH = Path(os.getenv("FORECAST_MODEL_PATH", str(BASE_DIR / "models" / "soil_forecast_sarimax.joblib")))
FORECAST_MIN_ROWS = int(os.getenv("FORECAST_MIN_ROWS", "24"))
FORECAST_RECENT_AVERAGE_HOURS = float(os.getenv("FORECAST_RECENT_AVERAGE_HOURS", "1"))
FORECAST_HORIZONS_HOURS = parse_forecast_horizons(os.getenv("FORECAST_HORIZONS_HOURS", "4,6,8"))
TELEGRAM_STATE_FILE = Path(os.getenv("TELEGRAM_STATE_FILE", str(BASE_DIR / ".telegram_state.json")))

# For most analog soil sensors: raw MCP3008 value is high when dry and low when wet.
SOIL_DRY_RAW = float(os.getenv("SOIL_DRY_RAW", "1.0"))
SOIL_WET_RAW = float(os.getenv("SOIL_WET_RAW", "0.51"))
DRY_PERCENT = float(os.getenv("DRY_PERCENT", "30"))
WET_PERCENT = float(os.getenv("WET_PERCENT", "70"))
FORECAST_DRY_PERCENT = float(os.getenv("FORECAST_DRY_PERCENT", str(DRY_PERCENT)))



def simulated_sensor_values(env=None):
    source = os.environ if env is None else env
    return (
        float(source.get("SIM_TEMPERATURE", "32")),
        float(source.get("SIM_HUMIDITY", "55")),
        float(source.get("SIM_SOIL_VALUE", "45")),
    )


def board_pin(pin_name):
    import board

    try:
        return getattr(board, pin_name)
    except AttributeError as exc:
        raise ValueError(f"Invalid DHT_PIN '{pin_name}'. Use D4 or D17, for example.") from exc


def setup_oled():
    try:
        import adafruit_ssd1306
        import board
        import busio
        from PIL import Image, ImageDraw, ImageFont

        i2c = busio.I2C(board.SCL, board.SDA)
        oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
        oled.fill(0)
        oled.show()

        image = Image.new("1", (oled.width, oled.height))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        return oled, image, draw, font
    except Exception as e:
        print(f"⚠️ OLED screen not detected ({e}). Continuing without display...")
        return None, None, None, None


def show_oled(oled, image, draw, font, reading):
    if oled is None:
        return
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    for index, line in enumerate(format_oled_lines(reading)):
        draw.text((0, index * 12), line, font=font, fill=255)
    oled.image(image)
    oled.show()


def read_dht11(dht):
    for attempt in range(3):
        try:
            return dht.temperature, dht.humidity
        except RuntimeError as exc:
            if attempt == 2:
                log_event("DHT_READ_FAILED", str(exc), DEBUG_MODE)
                return None, None
            time.sleep(2.0)  # DHT11 needs 2 seconds between reads
    return None, None


def read_soil_smoothed(soil_sensor, num_samples=10, delay=0.05):
    """Averaging/smoothing filter: takes multiple samples and returns the mean."""
    samples = []
    for _ in range(num_samples):
        samples.append(soil_sensor.value)
        time.sleep(delay)
    return sum(samples) / len(samples)


def read_hardware_values(dht, soil_sensor):
    temperature, humidity = read_dht11(dht)
    raw_value = read_soil_smoothed(soil_sensor)
    soil_value = raw_to_moisture_percent(
        raw_value,
        dry_raw=SOIL_DRY_RAW,
        wet_raw=SOIL_WET_RAW,
    )
    return temperature, humidity, soil_value


def build_reading_from_values(
    timestamp,
    temperature,
    humidity,
    soil_value,
    latest_features,
    forecast_result,
    control_mode,
    notification_status="",
    debug_status="OK",
    dry_soon_label="",
):
    previous_soil_value = clean_number(latest_features.get("soil_lag_1")) if latest_features else None
    moisture_change_rate = calculate_moisture_change_rate(soil_value, previous_soil_value)
    soil_status = classify_soil(
        soil_value,
        dry_threshold=DRY_PERCENT,
        wet_threshold=WET_PERCENT,
    )
    pump_status = decide_pump_status_with_forecast(soil_status, forecast_result.forecast_risk, control_mode)

    return SensorReading(
        timestamp=timestamp,
        temperature=temperature,
        humidity=humidity,
        soil_value=soil_value,
        previous_soil_value=previous_soil_value,
        moisture_change_rate=moisture_change_rate,
        vpd=clean_number(latest_features.get("vpd")) if latest_features else None,
        soil_lag_1=clean_number(latest_features.get("soil_lag_1")) if latest_features else None,
        soil_lag_2=clean_number(latest_features.get("soil_lag_2")) if latest_features else None,
        soil_lag_3=clean_number(latest_features.get("soil_lag_3")) if latest_features else None,
        soil_rolling_mean=clean_number(latest_features.get("soil_rolling_mean")) if latest_features else None,
        soil_rate_per_hour=clean_number(latest_features.get("soil_rate_per_hour")) if latest_features else None,
        soil_status=soil_status,
        pump_status=pump_status,
        forecast_soil_4hr=forecast_result.forecast_soil_4hr,
        forecast_soil_6hr=forecast_result.forecast_soil_6hr,
        forecast_soil_8hr=forecast_result.forecast_soil_8hr,
        forecast_risk=forecast_result.forecast_risk,
        forecast_recommendation=forecast_result.forecast_recommendation,
        ml_prediction=forecast_result.ml_prediction,
        dry_soon_label=dry_soon_label,
        notification_status=notification_status,
        debug_status=debug_status,
    )


def setup_hardware():
    import adafruit_dht
    import RPi.GPIO as GPIO
    from gpiozero import MCP3008

    dht = adafruit_dht.DHT11(board_pin(DHT_PIN))
    soil_sensor = MCP3008(channel=SOIL_CHANNEL)
    oled, image, draw, font = setup_oled()

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    return GPIO, dht, soil_sensor, oled, image, draw, font


def cleanup(gpio=None, dht=None, oled=None):
    print("Stopping system...")
    if gpio:
        gpio.output(RELAY_PIN, gpio.HIGH)
        gpio.cleanup()
    if dht:
        dht.exit()
    if oled:
        oled.fill(0)
        oled.show()


def log_pump_reason(reading):
    if reading.pump_status != "ON":
        return
    if reading.soil_status == "DRY":
        log_event("PUMP_ON_DRY", "soil is dry", DEBUG_MODE)
    elif reading.forecast_risk == "Dry Forecast":
        log_event("PUMP_ON_FORECAST_DRY", "forecast predicts future dry soil", DEBUG_MODE)


def run_timed_pump(gpio, reading):
    """Run pump for a fixed duration based on trigger reason, then turn it off."""
    if not gpio or reading.pump_status != "ON":
        return

    if reading.soil_status == "DRY":
        duration = PUMP_DURATION_SECONDS
        reason = "soil DRY"
    elif reading.forecast_risk == "Dry Forecast":
        duration = PUMP_FORECAST_DURATION_SECONDS
        reason = "4h forecast DRY"
    else:
        return

    print(f"Pump ON ({reason}) — running for {duration}s...")
    set_pump_output(gpio, RELAY_PIN, "ON")
    time.sleep(duration)
    set_pump_output(gpio, RELAY_PIN, "OFF")
    print("Pump OFF — timer complete.")


def clean_number(value):
    if value is None:
        return None
    try:
        if value != value:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def run_cycle(gpio, dht, soil_sensor, oled, image, draw, font, model_bundle, favoriot_config, telegram_config):
    if SIMULATION_MODE:
        temperature, humidity, soil_value = simulated_sensor_values()
    else:
        temperature, humidity, soil_value = read_hardware_values(dht, soil_sensor)

    timestamp = datetime.now()
    history = load_forecast_history(CSV_FILE)
    forecast_history = append_current_reading(history, timestamp, temperature, humidity, soil_value)
    enriched_history = enrich_forecast_features(forecast_history)
    latest_features = enriched_history.iloc[-1].to_dict() if not enriched_history.empty else {}
    forecast_result = forecast_soil_moisture(
        model_bundle,
        forecast_history,
        horizons_hours=FORECAST_HORIZONS_HOURS,
        recent_average_hours=FORECAST_RECENT_AVERAGE_HOURS,
        dry_threshold=FORECAST_DRY_PERCENT,
        control_mode=ML_CONTROL_MODE,
    )
    if not model_bundle.is_ready and len(enriched_history.dropna(subset=["soil_value"])) < FORECAST_MIN_ROWS:
        forecast_result.status_code = FORECAST_NOT_ENOUGH_DATA

    reading = build_reading_from_values(
        timestamp=timestamp,
        temperature=temperature,
        humidity=humidity,
        soil_value=soil_value,
        latest_features=latest_features,
        forecast_result=forecast_result,
        control_mode=ML_CONTROL_MODE,
        debug_status=forecast_result.status_code,
    )

    risk_events = detect_risk_events(reading)
    event_text = ",".join(risk_events) if risk_events else "NONE"
    telegram_status = send_telegram_alerts(
        telegram_config,
        risk_events,
        reading,
        TELEGRAM_STATE_FILE,
    )
    reading = replace(
        reading,
        notification_status=f"{event_text};{telegram_status}",
        debug_status=forecast_result.status_code,
    )

    if gpio:
        run_timed_pump(gpio, reading)
    log_pump_reason(reading)

    if SAVE_DATA:
        write_csv_reading(CSV_FILE, reading)
        log_event("CSV_WRITE_OK", f"saved row to {CSV_FILE}", DEBUG_MODE)
        write_db_reading(DB_FILE, reading)
        log_event("DB_WRITE_OK", f"saved row to {DB_FILE}", DEBUG_MODE)
        
    send_to_favoriot(favoriot_config, reading, logger=lambda message: log_event("FAVORIOT", message, DEBUG_MODE))
    show_oled(oled, image, draw, font, reading)

    print("----------------------")
    print("Time:", reading.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
    print("Soil moisture:", round(reading.soil_value, 1), "%")
    print("Soil status:", reading.soil_status)
    print("Forecast 4h:", reading.forecast_soil_4hr)
    print("Forecast 6h:", reading.forecast_soil_6hr)
    print("Forecast 8h:", reading.forecast_soil_8hr)
    print("Forecast risk:", reading.forecast_risk)
    print("Recommendation:", reading.forecast_recommendation)
    print("Pump:", reading.pump_status)
    print("Notification:", reading.notification_status)
    if reading.temperature is None or reading.humidity is None:
        print("DHT11 reading error")
    else:
        print("Temp:", reading.temperature, "C")
        print("Humidity:", reading.humidity, "%")


def main():
    ensure_csv_header(CSV_FILE)
    init_db(DB_FILE)  # create sensor_data.db if it doesn't exist
    favoriot_config = load_favoriot_config()
    telegram_config = telegram_config_from_env()
    model_bundle = load_forecast_model(FORECAST_MODEL_PATH)

    diagnostics = build_startup_diagnostics(
        dht_pin=DHT_PIN,
        soil_channel=SOIL_CHANNEL,
        relay_pin=RELAY_PIN,
        csv_path=CSV_FILE,
        favoriot_config=favoriot_config,
        telegram_config=telegram_config,
        model_path=FORECAST_MODEL_PATH,
        simulation_mode=SIMULATION_MODE,
    )
    if model_bundle.status_code == FORECAST_MODEL_MISSING:
        diagnostics["FORECAST_MODEL"] = FORECAST_MODEL_MISSING
    debug_status = debug_status_from_diagnostics(diagnostics)

    print("Smart plant system started. Press Ctrl+C to stop.")
    print(f"CSV file: {CSV_FILE}")
    print(f"Mode: {'SIMULATION' if SIMULATION_MODE else 'HARDWARE'}")
    print(f"Forecast model: {model_bundle.status_code}")
    print(f"Forecast horizons: {FORECAST_HORIZONS_HOURS} hours")
    print(f"Forecast minimum training rows: {FORECAST_MIN_ROWS}")
    print(f"Startup diagnostics: {diagnostics}")
    print(f"Debug status: {debug_status}")

    gpio = dht = soil_sensor = oled = image = draw = font = None
    if not SIMULATION_MODE:
        gpio, dht, soil_sensor, oled, image, draw, font = setup_hardware()

    try:
        while True:
            try:
                run_cycle(gpio, dht, soil_sensor, oled, image, draw, font, model_bundle, favoriot_config, telegram_config)
            except Exception as exc:
                log_event("LOOP_ERROR", str(exc), True)
                if gpio:
                    gpio.output(RELAY_PIN, gpio.HIGH)

            if RUN_ONCE:
                break
            time.sleep(READ_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        pass
    finally:
        cleanup(gpio, dht, oled)


if __name__ == "__main__":
    main()
