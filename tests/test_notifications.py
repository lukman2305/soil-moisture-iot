import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from plant_monitor.app import SensorReading
from plant_monitor.notifications import (
    TelegramConfig,
    detect_risk_events,
    send_telegram_alerts,
)


class FakeResponse:
    status_code = 200
    text = "ok"


class NotificationsTest(unittest.TestCase):
    def reading(self, **overrides):
        data = {
            "timestamp": datetime(2026, 6, 12, 10, 30, 0),
            "temperature": 35.0,
            "humidity": 45.0,
            "soil_value": 24.0,
            "previous_soil_value": 34.0,
            "moisture_change_rate": -10.0,
            "soil_status": "DRY",
            "pump_status": "ON",
            "ml_prediction": "Dry Soon",
            "dry_soon_label": "Dry Soon",
            "notification_status": "",
            "debug_status": "OK",
        }
        data.update(overrides)
        return SensorReading(**data)

    def test_detect_risk_events_reports_all_risk_states(self):
        events = detect_risk_events(self.reading(temperature=None, soil_status="WET"))

        self.assertEqual(events, ["Dry Soon", "WET", "DHT Missing"])

    def test_send_telegram_alerts_skips_when_not_configured(self):
        calls = []
        status = send_telegram_alerts(
            TelegramConfig(enabled=True, bot_token="", chat_id="", cooldown_seconds=1800),
            ["Dry Soon"],
            self.reading(),
            state_path=None,
            now=datetime(2026, 6, 12, 10, 30, 0),
            post=lambda *args, **kwargs: calls.append((args, kwargs)),
        )

        self.assertEqual(status, "TELEGRAM_SKIPPED")
        self.assertEqual(calls, [])

    def test_send_telegram_alerts_respects_cooldown_per_warning_type(self):
        calls = []

        def fake_post(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeResponse()

        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "telegram_state.json"
            config = TelegramConfig(
                enabled=True,
                bot_token="token",
                chat_id="chat",
                cooldown_seconds=1800,
            )
            now = datetime(2026, 6, 12, 10, 30, 0)

            first = send_telegram_alerts(config, ["Dry Soon"], self.reading(), state_path, now, post=fake_post)
            second = send_telegram_alerts(
                config,
                ["Dry Soon"],
                self.reading(),
                state_path,
                now + timedelta(minutes=10),
                post=fake_post,
            )
            third = send_telegram_alerts(
                config,
                ["Dry Soon"],
                self.reading(),
                state_path,
                now + timedelta(minutes=31),
                post=fake_post,
            )

        self.assertEqual(first, "TELEGRAM_SENT:Dry Soon")
        self.assertEqual(second, "TELEGRAM_COOLDOWN:Dry Soon")
        self.assertEqual(third, "TELEGRAM_SENT:Dry Soon")
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
