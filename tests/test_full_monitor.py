import unittest
from datetime import datetime

from full_monitor import build_reading_from_values, simulated_sensor_values
from plant_monitor.forecast import ForecastResult


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
        forecast_result = ForecastResult(
            forecast_soil_4hr=28.0,
            forecast_soil_6hr=35.0,
            forecast_soil_8hr=42.0,
            forecast_risk="Dry Forecast",
            forecast_recommendation="Forecast dry. Pump may turn ON early because ML_CONTROL_MODE=control.",
            ml_prediction="Forecast Dry",
            status_code="OK",
        )
        reading = build_reading_from_values(
            timestamp=datetime(2026, 6, 12, 10, 30, 0),
            temperature=35.0,
            humidity=45.0,
            soil_value=42.0,
            latest_features={
                "soil_lag_1": 50.0,
                "vpd": 3.1,
                "soil_rolling_mean": 45.0,
                "soil_rate_per_hour": -8.0,
            },
            forecast_result=forecast_result,
            control_mode="control",
            notification_status="Forecast Dry",
            debug_status="OK",
        )

        self.assertEqual(reading.moisture_change_rate, -8.0)
        self.assertEqual(reading.soil_status, "OPTIMAL")
        self.assertEqual(reading.pump_status, "ON")
        self.assertEqual(reading.ml_prediction, "Forecast Dry")
        self.assertEqual(reading.forecast_soil_4hr, 28.0)


if __name__ == "__main__":
    unittest.main()
