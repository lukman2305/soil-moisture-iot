import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests


@dataclass(frozen=True)
class TelegramConfig:
    enabled: bool
    bot_token: str
    chat_id: str
    cooldown_seconds: int = 1800

    @property
    def is_configured(self):
        return self.enabled and bool(self.bot_token.strip()) and bool(self.chat_id.strip())


def detect_risk_events(reading):
    events = []
    if getattr(reading, "forecast_risk", "") == "Dry Forecast" or reading.ml_prediction == "Forecast Dry":
        events.append("Forecast Dry")
    elif reading.ml_prediction == "Dry Soon":
        events.append("Dry Soon")
    if reading.soil_status == "DRY":
        events.append("DRY")
    if reading.soil_status == "WET":
        events.append("WET")
    if reading.temperature is None or reading.humidity is None:
        events.append("DHT Missing")
    return events


def format_notification_message(events, reading):
    event_text = ", ".join(events) if events else "No risk"
    return (
        "Smart Plant Alert\n"
        f"Risk: {event_text}\n"
        f"Soil: {round(reading.soil_value, 1)}%\n"
        f"Temp: {reading.temperature if reading.temperature is not None else 'N/A'} C\n"
        f"Humidity: {reading.humidity if reading.humidity is not None else 'N/A'}%\n"
        f"Pump: {reading.pump_status}\n"
        f"ML: {reading.ml_prediction}\n"
        f"Forecast 4h: {getattr(reading, 'forecast_soil_4hr', None) if getattr(reading, 'forecast_soil_4hr', None) is not None else 'N/A'}%\n"
        f"Forecast 6h: {getattr(reading, 'forecast_soil_6hr', None) if getattr(reading, 'forecast_soil_6hr', None) is not None else 'N/A'}%\n"
        f"Forecast 8h: {getattr(reading, 'forecast_soil_8hr', None) if getattr(reading, 'forecast_soil_8hr', None) is not None else 'N/A'}%\n"
        f"Recommendation: {getattr(reading, 'forecast_recommendation', 'N/A')}"
    )


def _load_state(state_path):
    if not state_path:
        return {}
    path = Path(state_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state_path, state):
    if not state_path:
        return
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def send_telegram_alerts(config, events, reading, state_path, now=None, post=requests.post):
    if not events:
        return "NO_RISK"
    if not config.is_configured:
        return "TELEGRAM_SKIPPED"

    current_time = now or datetime.now()
    state = _load_state(state_path)
    due_events = []
    cooldown_events = []

    for event in events:
        last_sent = state.get(event)
        if last_sent:
            try:
                elapsed = (current_time - datetime.fromisoformat(last_sent)).total_seconds()
            except ValueError:
                elapsed = config.cooldown_seconds + 1
            if elapsed < config.cooldown_seconds:
                cooldown_events.append(event)
                continue
        due_events.append(event)

    if not due_events:
        return "TELEGRAM_COOLDOWN:" + ",".join(cooldown_events)

    message = format_notification_message(due_events, reading)
    url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
    response = post(
        url,
        json={"chat_id": config.chat_id, "text": message},
        timeout=5,
    )
    if response.status_code not in (200, 201):
        return f"TELEGRAM_ERROR:{response.status_code}"

    for event in due_events:
        state[event] = current_time.isoformat()
    _save_state(state_path, state)
    return "TELEGRAM_SENT:" + ",".join(due_events)
