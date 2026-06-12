import os
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from plant_monitor.app import (
    SensorReading,
    ensure_csv_header,
    format_oled_lines,
    read_latest_soil_value,
    send_to_favoriot,
    set_pump_output,
    write_csv_reading,
)
from plant_monitor.debug import build_startup_diagnostics, debug_status_from_diagnostics, log_event
from plant_monitor.env import load_env_file
from plant_monitor.logic import (
    classify_soil,
    decide_pump_status,
    decide_pump_status_with_ml,
    load_favoriot_config,
    raw_to_moisture_percent,
)
from plant_monitor.ml import calculate_moisture_change_rate, load_or_train_model, predict_dryness
from plant_monitor.notifications import detect_risk_events, send_telegram_alerts
from plant_monitor.settings import (
    debug_mode_enabled,
    ml_control_mode,
    read_interval_seconds,
    run_once_enabled,
    simulation_mode_enabled,
    telegram_config_from_env,
)


BASE_DIR = Path(__file__).resolve().parent
load_env_file(BASE_DIR / ".env")

CSV_FILE = Path(os.getenv("CSV_FILE", str(BASE_DIR / "plant_data.csv")))
RELAY_PIN = int(os.getenv("RELAY_PIN", "18"))
SOIL_CHANNEL = int(os.getenv("SOIL_CHANNEL", "0"))
DHT_PIN = os.getenv("DHT_PIN", "D4").upper()
READ_INTERVAL_SECONDS = read_interval_seconds()
ML_CONTROL_MODE = ml_control_mode()
DEBUG_MODE = debug_mode_enabled()
SIMULATION_MODE = simulation_mode_enabled()
RUN_ONCE = run_once_enabled()

MODEL_PATH = Path(os.getenv("MODEL_PATH", str(BASE_DIR / "models" / "dryness_model.joblib")))
TRAINING_CSV_FILE = Path(os.getenv("TRAINING_CSV_FILE", str(BASE_DIR / "data" / "training_smart_agriculture.csv")))
TELEGRAM_STATE_FILE = Path(os.getenv("TELEGRAM_STATE_FILE", str(BASE_DIR / ".telegram_state.json")))

# For most analog soil sensors: raw MCP3008 value is high when dry and low when wet.
SOIL_DRY_RAW = float(os.getenv("SOIL_DRY_RAW", "1.0"))
SOIL_WET_RAW = float(os.getenv("SOIL_WET_RAW", "0.0"))
DRY_PERCENT = float(os.getenv("DRY_PERCENT", "30"))
WET_PERCENT = float(os.getenv("WET_PERCENT", "70"))


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


def show_oled(oled, image, draw, font, reading):
    if oled is None:
        return
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    for index, line in enumerate(format_oled_lines(reading)):
        draw.text((0, index * 12), line, font=font, fill=255)
    oled.image(image)
    oled.show()


def read_dht11(dht):
    try:
        return dht.temperature, dht.humidity
    except RuntimeError as exc:
        log_event("DHT_READ_FAILED", str(exc), DEBUG_MODE)
        return None, None


def read_hardware_values(dht, soil_sensor):
    temperature, humidity = read_dht11(dht)
    soil_value = raw_to_moisture_percent(
        soil_sensor.value,
        dry_raw=SOIL_DRY_RAW,
        wet_raw=SOIL_WET_RAW,
    )
    return temperature, humidity, soil_value


def build_reading_from_values(
    timestamp,
    temperature,
    humidity,
    soil_value,
    previous_soil_value,
    ml_prediction,
    ml_control_mode,
    notification_status="",
    debug_status="OK",
    dry_soon_label="",
):
    moisture_change_rate = calculate_moisture_change_rate(soil_value, previous_soil_value)
    soil_status = classify_soil(
        soil_value,
        dry_threshold=DRY_PERCENT,
        wet_threshold=WET_PERCENT,
    )
    pump_status = decide_pump_status_with_ml(soil_status, ml_prediction, ml_control_mode)

    return SensorReading(
        timestamp=timestamp,
        temperature=temperature,
        humidity=humidity,
        soil_value=soil_value,
        previous_soil_value=previous_soil_value,
        moisture_change_rate=moisture_change_rate,
        soil_status=soil_status,
        pump_status=pump_status,
        ml_prediction=ml_prediction,
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
    elif reading.ml_prediction == "Dry Soon":
        log_event("PUMP_ON_ML_DRY_SOON", "ML predicts dry soon", DEBUG_MODE)


def run_cycle(gpio, dht, soil_sensor, oled, image, draw, font, model_bundle, favoriot_config, telegram_config):
    previous_soil_value = read_latest_soil_value(CSV_FILE)

    if SIMULATION_MODE:
        temperature, humidity, soil_value = simulated_sensor_values()
    else:
        temperature, humidity, soil_value = read_hardware_values(dht, soil_sensor)

    base_soil_status = classify_soil(soil_value, dry_threshold=DRY_PERCENT, wet_threshold=WET_PERCENT)
    base_pump_status = decide_pump_status(base_soil_status)
    moisture_change_rate = calculate_moisture_change_rate(soil_value, previous_soil_value)
    ml_prediction = predict_dryness(
        model_bundle,
        soil_value=soil_value,
        temperature=temperature,
        humidity=humidity,
        previous_soil_value=previous_soil_value,
        moisture_change_rate=moisture_change_rate,
        pump_status=base_pump_status,
    )

    reading = build_reading_from_values(
        timestamp=datetime.now(),
        temperature=temperature,
        humidity=humidity,
        soil_value=soil_value,
        previous_soil_value=previous_soil_value,
        ml_prediction=ml_prediction,
        ml_control_mode=ML_CONTROL_MODE,
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
        debug_status="OK",
    )

    if gpio:
        set_pump_output(gpio, RELAY_PIN, reading.pump_status)
    log_pump_reason(reading)

    write_csv_reading(CSV_FILE, reading)
    log_event("CSV_WRITE_OK", f"saved row to {CSV_FILE}", DEBUG_MODE)
    send_to_favoriot(favoriot_config, reading, logger=lambda message: log_event("FAVORIOT", message, DEBUG_MODE))
    show_oled(oled, image, draw, font, reading)

    print("----------------------")
    print("Time:", reading.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
    print("Soil moisture:", round(reading.soil_value, 1), "%")
    print("Soil status:", reading.soil_status)
    print("ML prediction:", reading.ml_prediction)
    print("Pump:", reading.pump_status)
    print("Notification:", reading.notification_status)
    if reading.temperature is None or reading.humidity is None:
        print("DHT11 reading error")
    else:
        print("Temp:", reading.temperature, "C")
        print("Humidity:", reading.humidity, "%")


def main():
    ensure_csv_header(CSV_FILE)
    favoriot_config = load_favoriot_config()
    telegram_config = telegram_config_from_env()
    model_bundle = load_or_train_model(MODEL_PATH, TRAINING_CSV_FILE)

    diagnostics = build_startup_diagnostics(
        dht_pin=DHT_PIN,
        soil_channel=SOIL_CHANNEL,
        relay_pin=RELAY_PIN,
        csv_path=CSV_FILE,
        favoriot_config=favoriot_config,
        telegram_config=telegram_config,
        model_path=MODEL_PATH,
        simulation_mode=SIMULATION_MODE,
    )
    debug_status = debug_status_from_diagnostics(diagnostics)

    print("Smart plant system started. Press Ctrl+C to stop.")
    print(f"CSV file: {CSV_FILE}")
    print(f"Mode: {'SIMULATION' if SIMULATION_MODE else 'HARDWARE'}")
    print(f"ML model: {model_bundle.status_code}")
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
