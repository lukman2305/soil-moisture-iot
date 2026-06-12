import unittest
from datetime import datetime

from full_monitor import build_reading_from_values, simulated_sensor_values


class FullMonitorSimulationTest(unittest.TestCase):
    def test_simulated_sensor_values_are_read_from_environment(self):
        values = simulated_sensor_values(
            {
                "SIM_TEMPERATURE": "31",
                "SIM_HUMIDITY": "64",
                "SIM_SOIL_VALUE": "44",
            }
        )

        self.assertEqual(values, (31.0, 64.0, 44.0))

    def test_build_reading_from_values_includes_prediction_and_trend(self):
        reading = build_reading_from_values(
            timestamp=datetime(2026, 6, 12, 10, 30, 0),
            temperature=35.0,
            humidity=45.0,
            soil_value=42.0,
            previous_soil_value=50.0,
            ml_prediction="Dry Soon",
            ml_control_mode="control",
            notification_status="Dry Soon",
            debug_status="OK",
        )

        self.assertEqual(reading.moisture_change_rate, -8.0)
        self.assertEqual(reading.soil_status, "OPTIMAL")
        self.assertEqual(reading.pump_status, "ON")
        self.assertEqual(reading.ml_prediction, "Dry Soon")


if __name__ == "__main__":
    unittest.main()
