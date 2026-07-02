import os
import unittest

from plant_monitor.logic import (
    FavoriotConfig,
    classify_soil,
    decide_pump_status_with_forecast,
    decide_pump_status_with_ml,
    decide_pump_status,
    load_favoriot_config,
    raw_to_moisture_percent,
)


class PlantMonitorLogicTest(unittest.TestCase):
    def test_raw_to_moisture_percent_maps_dry_high_sensor_to_wet_percentage(self):
        self.assertEqual(raw_to_moisture_percent(1.0, dry_raw=1.0, wet_raw=0.0), 0.0)
        self.assertEqual(raw_to_moisture_percent(0.0, dry_raw=1.0, wet_raw=0.0), 100.0)
        self.assertEqual(raw_to_moisture_percent(0.5, dry_raw=1.0, wet_raw=0.0), 50.0)

    def test_raw_to_moisture_percent_clamps_out_of_range_values(self):
        self.assertEqual(raw_to_moisture_percent(1.2, dry_raw=1.0, wet_raw=0.0), 0.0)
        self.assertEqual(raw_to_moisture_percent(-0.2, dry_raw=1.0, wet_raw=0.0), 100.0)

    def test_classify_soil_uses_assignment_thresholds(self):
        self.assertEqual(classify_soil(29.9), "DRY")
        self.assertEqual(classify_soil(30.0), "OPTIMAL")
        self.assertEqual(classify_soil(70.0), "OPTIMAL")
        self.assertEqual(classify_soil(70.1), "WET")

    def test_decide_pump_status_only_waters_dry_soil(self):
        self.assertEqual(decide_pump_status("DRY"), "ON")
        self.assertEqual(decide_pump_status("OPTIMAL"), "OFF")
        self.assertEqual(decide_pump_status("WET"), "OFF")

    def test_decide_pump_status_with_ml_control_mode(self):
        self.assertEqual(decide_pump_status_with_ml("DRY", "Not Dry Soon", "recommend"), "ON")
        self.assertEqual(decide_pump_status_with_ml("OPTIMAL", "Dry Soon", "recommend"), "OFF")
        self.assertEqual(decide_pump_status_with_ml("OPTIMAL", "Dry Soon", "control"), "ON")
        self.assertEqual(decide_pump_status_with_ml("WET", "Dry Soon", "control"), "OFF")

    def test_decide_pump_status_with_forecast_respects_recommend_and_control(self):
        # Current soil DRY → always pump ON regardless of mode or forecast
        self.assertEqual(decide_pump_status_with_forecast("DRY", "OK", "recommend"), "ON")
        self.assertEqual(decide_pump_status_with_forecast("DRY", "Dry Forecast", "control", forecast_soil_4hr=20.0), "ON")

        # Current soil WET → always pump OFF
        self.assertEqual(decide_pump_status_with_forecast("WET", "Dry Forecast", "control", forecast_soil_4hr=20.0), "OFF")

        # 4h forecast DRY + control → pump ON early
        self.assertEqual(decide_pump_status_with_forecast("OPTIMAL", "Dry Forecast", "control", forecast_soil_4hr=20.0), "ON")

        # 4h forecast DRY + recommend → pump OFF (just alert)
        self.assertEqual(decide_pump_status_with_forecast("OPTIMAL", "Dry Forecast", "recommend", forecast_soil_4hr=20.0), "OFF")

        # 6h/8h forecast DRY but 4h OPTIMAL + control → pump OFF (alert only)
        self.assertEqual(decide_pump_status_with_forecast("OPTIMAL", "Dry Forecast", "control", forecast_soil_4hr=55.0), "OFF")

        # No 4h value provided + control → pump OFF (not enough info)
        self.assertEqual(decide_pump_status_with_forecast("OPTIMAL", "Dry Forecast", "control", forecast_soil_4hr=None), "OFF")

    def test_load_favoriot_config_reads_env_without_hardcoded_secret(self):
        env = {
            "FAVORIOT_API_KEY": "real-key-from-env",
            "FAVORIOT_DEVICE_DEVELOPER_ID": "device-default@user",
        }

        config = load_favoriot_config(env)

        self.assertEqual(
            config,
            FavoriotConfig(
                api_key="real-key-from-env",
                device_developer_id="device-default@user",
                url="https://apiv2.favoriot.com/v2/streams",
            ),
        )
        self.assertTrue(config.is_configured)

    def test_load_favoriot_config_treats_missing_values_as_unconfigured(self):
        config = load_favoriot_config({})

        self.assertFalse(config.is_configured)
        self.assertEqual(config.api_key, "")
        self.assertEqual(config.device_developer_id, "")


if __name__ == "__main__":
    unittest.main()
