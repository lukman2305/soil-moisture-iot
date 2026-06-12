from datetime import datetime
from pathlib import Path


def format_log_line(code, message, now=None):
    timestamp = now or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{timestamp} [{code}] {message}"


def log_event(code, message, debug_enabled=True, logger=print):
    if debug_enabled:
        logger(format_log_line(code, message))


def build_startup_diagnostics(
    dht_pin,
    soil_channel,
    relay_pin,
    csv_path,
    favoriot_config,
    telegram_config,
    model_path,
    simulation_mode,
):
    diagnostics = {}
    diagnostics["DHT_PIN"] = "SIMULATION" if simulation_mode else f"OK:{dht_pin}"
    diagnostics["MCP3008_CHANNEL"] = "SIMULATION" if simulation_mode else f"OK:{soil_channel}"
    diagnostics["RELAY_PIN"] = "SIMULATION" if simulation_mode else f"OK:{relay_pin}"

    csv_parent = Path(csv_path).parent
    diagnostics["CSV_PATH"] = "OK" if csv_parent.exists() else "CSV_PARENT_MISSING"
    diagnostics["FAVORIOT_CONFIG"] = "OK" if favoriot_config.is_configured else "OPTIONAL_NOT_CONFIGURED"

    if telegram_config.enabled and telegram_config.is_configured:
        diagnostics["TELEGRAM_CONFIG"] = "OK"
    elif telegram_config.enabled:
        diagnostics["TELEGRAM_CONFIG"] = "TELEGRAM_MISSING_SECRET"
    else:
        diagnostics["TELEGRAM_CONFIG"] = "TELEGRAM_DISABLED"

    diagnostics["MODEL_FILE"] = "OK" if Path(model_path).exists() else "MODEL_MISSING"
    return diagnostics


def debug_status_from_diagnostics(diagnostics):
    problem_codes = [
        code
        for code in diagnostics.values()
        if code not in ("OK", "OPTIONAL_NOT_CONFIGURED", "TELEGRAM_DISABLED")
        and not str(code).startswith("OK:")
        and code != "SIMULATION"
    ]
    return "OK" if not problem_codes else ",".join(problem_codes)
