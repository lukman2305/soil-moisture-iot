import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from plant_monitor.app import (
    CSV_HEADER,
    SensorReading,
    build_favoriot_payload,
    ensure_csv_header,
    format_oled_lines,
    send_to_favoriot,
    set_pump_output,
    write_csv_reading,
)
from plant_monitor.logic import FavoriotConfig


class FakeGPIO:
    LOW = 0
    HIGH = 1

    def __init__(self):
        self.calls = []

    def output(self, pin, level):
        self.calls.append((pin, level))


class FakeResponse:
    def __init__(self, status_code=201, text="created"):
        self.status_code = status_code
        self.text = text


class PlantMonitorAppTest(unittest.TestCase):
    def sample_reading(self):
        return SensorReading(
            timestamp=datetime(2026, 6, 12, 10, 30, 0),
            temperature=29.0,
            humidity=72.0,
            soil_value=24.5,
            previous_soil_value=30.0,
            moisture_change_rate=-5.5,
            soil_status="DRY",
            pump_status="ON",
            ml_prediction="Dry Soon",
            dry_soon_label="Dry Soon",
            notification_status="DRY,Dry Soon",
            debug_status="OK",
        )

    def test_ensure_csv_header_creates_expected_assignment_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "plant_data.csv"

            ensure_csv_header(csv_path)

            with csv_path.open(newline="") as file:
                rows = list(csv.reader(file))

        self.assertEqual(rows, [CSV_HEADER])

    def test_write_csv_reading_appends_required_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "plant_data.csv"
            ensure_csv_header(csv_path)

            write_csv_reading(csv_path, self.sample_reading())

            with csv_path.open(newline="") as file:
                rows = list(csv.reader(file))

        self.assertEqual(
            rows[1],
            [
                "2026-06-12 10:30:00",
                "29.0",
                "72.0",
                "24.5",
                "30.0",
                "-5.5",
                "DRY",
                "ON",
                "Dry Soon",
                "Dry Soon",
                "DRY,Dry Soon",
                "OK",
            ],
        )

    def test_build_favoriot_payload_matches_dashboard_fields(self):
        payload = build_favoriot_payload("device-default@user", self.sample_reading())

        self.assertEqual(payload["device_developer_id"], "device-default@user")
        self.assertEqual(
            payload["data"],
            {
                "temperature": 29.0,
                "humidity": 72.0,
                "soil_value": 24.5,
                "soil_status": "DRY",
                "pump_status": "ON",
                "ml_prediction": "Dry Soon",
                "notification_status": "DRY,Dry Soon",
            },
        )

    def test_send_to_favoriot_skips_unconfigured_credentials(self):
        calls = []

        ok = send_to_favoriot(
            FavoriotConfig(api_key="", device_developer_id="", url="https://example.invalid"),
            self.sample_reading(),
            post=lambda *args, **kwargs: calls.append((args, kwargs)),
        )

        self.assertFalse(ok)
        self.assertEqual(calls, [])

    def test_send_to_favoriot_posts_configured_payload(self):
        calls = []

        def fake_post(url, json, headers, timeout):
            calls.append((url, json, headers, timeout))
            return FakeResponse()

        ok = send_to_favoriot(
            FavoriotConfig(
                api_key="key-from-env",
                device_developer_id="device-default@user",
                url="https://apiv2.favoriot.com/v2/streams",
            ),
            self.sample_reading(),
            post=fake_post,
        )

        self.assertTrue(ok)
        self.assertEqual(calls[0][0], "https://apiv2.favoriot.com/v2/streams")
        self.assertEqual(calls[0][2]["apikey"], "key-from-env")
        self.assertEqual(calls[0][3], 5)

    def test_set_pump_output_uses_active_low_relay(self):
        gpio = FakeGPIO()

        set_pump_output(gpio, relay_pin=18, pump_status="ON")
        set_pump_output(gpio, relay_pin=18, pump_status="OFF")

        self.assertEqual(gpio.calls, [(18, gpio.LOW), (18, gpio.HIGH)])

    def test_format_oled_lines_fits_core_status_data(self):
        lines = format_oled_lines(self.sample_reading())

        self.assertEqual(lines, ["SMART PLANT", "Temp: 29.0 C", "Humid: 72.0%", "Soil: 24.5%", "ML:Dry Soon P:ON"])


if __name__ == "__main__":
    unittest.main()
