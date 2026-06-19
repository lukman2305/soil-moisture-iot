import tempfile
import unittest
from pathlib import Path

from plant_monitor.debug import build_startup_diagnostics, format_log_line
from plant_monitor.logic import FavoriotConfig
from plant_monitor.notifications import TelegramConfig


class DebugDiagnosticsTest(unittest.TestCase):
    def test_build_startup_diagnostics_reports_key_config_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "plant_data.csv"
            model_path = Path(directory) / "dryness_model.joblib"

            diagnostics = build_startup_diagnostics(
                dht_pin="D4",
                soil_channel=0,
                relay_pin=18,
                csv_path=csv_path,
                favoriot_config=FavoriotConfig(api_key="", device_developer_id=""),
                telegram_config=TelegramConfig(enabled=True, bot_token="token", chat_id="chat", cooldown_seconds=1800),
                model_path=model_path,
                simulation_mode=False,
            )

        self.assertEqual(diagnostics["DHT_PIN"], "OK:D4")
        self.assertEqual(diagnostics["MCP3008_CHANNEL"], "OK:0")
        self.assertEqual(diagnostics["RELAY_PIN"], "OK:18")
        self.assertEqual(diagnostics["FAVORIOT_CONFIG"], "OPTIONAL_NOT_CONFIGURED")
        self.assertEqual(diagnostics["TELEGRAM_CONFIG"], "OK")
        self.assertEqual(diagnostics["MODEL_FILE"], "MODEL_MISSING")

    def test_format_log_line_includes_reason_code(self):
        line = format_log_line("CSV_WRITE_OK", "saved row", now="2026-06-12 10:30:00")

        self.assertEqual(line, "2026-06-12 10:30:00 [CSV_WRITE_OK] saved row")


if __name__ == "__main__":
    unittest.main()
