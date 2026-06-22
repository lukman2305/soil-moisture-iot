import os

from plant_monitor.notifications import TelegramConfig


DEFAULT_READ_INTERVAL_SECONDS = 600
DEFAULT_PUMP_DURATION_SECONDS = 10
DEFAULT_PUMP_FORECAST_DURATION_SECONDS = 5


def read_interval_seconds(env=None):
    source = os.environ if env is None else env
    return float(source.get("READ_INTERVAL_SECONDS", DEFAULT_READ_INTERVAL_SECONDS))


def pump_duration_seconds(env=None):
    source = os.environ if env is None else env
    return float(source.get("PUMP_DURATION_SECONDS", DEFAULT_PUMP_DURATION_SECONDS))


def pump_forecast_duration_seconds(env=None):
    source = os.environ if env is None else env
    return float(source.get("PUMP_FORECAST_DURATION_SECONDS", DEFAULT_PUMP_FORECAST_DURATION_SECONDS))


def _truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def debug_mode_enabled(env=None):
    source = os.environ if env is None else env
    return _truthy(source.get("DEBUG_MODE", "false"))


def simulation_mode_enabled(env=None):
    source = os.environ if env is None else env
    return _truthy(source.get("SIMULATION_MODE", "false"))


def run_once_enabled(env=None):
    source = os.environ if env is None else env
    return _truthy(source.get("RUN_ONCE", "false"))


def ml_control_mode(env=None):
    source = os.environ if env is None else env
    value = source.get("ML_CONTROL_MODE", "recommend").strip().lower()
    return value if value in {"recommend", "control"} else "recommend"


def telegram_config_from_env(env=None):
    source = os.environ if env is None else env
    return TelegramConfig(
        enabled=_truthy(source.get("TELEGRAM_ENABLED", "false")),
        bot_token=source.get("TELEGRAM_BOT_TOKEN", "").strip(),
        chat_id=source.get("TELEGRAM_CHAT_ID", "").strip(),
        cooldown_seconds=int(source.get("NOTIFICATION_COOLDOWN_SECONDS", "1800")),
    )
