import unittest

import pandas as pd

from streamlit_app import chart_sections, streamlit_refresh_seconds


class StreamlitDashboardTest(unittest.TestCase):
    def test_chart_sections_keep_temperature_and_humidity_separate(self):
        frame = pd.DataFrame(
            {
                "timestamp": ["2026-06-14 10:00:00"],
                "soil_value": [45.0],
                "temperature": [32.0],
                "humidity": [55.0],
                "moisture_change_rate": [-5.0],
                "forecast_soil_4hr": [40.0],
                "forecast_soil_6hr": [34.0],
                "forecast_soil_8hr": [27.0],
            }
        )

        sections = chart_sections(frame)

        self.assertEqual(
            sections,
            [
                ("Soil Moisture Trend", ["soil_value"]),
                ("Temperature Trend", ["temperature"]),
                ("Humidity Trend", ["humidity"]),
                ("Moisture Change Rate", ["moisture_change_rate"]),
                ("Forecast Soil Moisture", ["soil_value", "forecast_soil_4hr", "forecast_soil_6hr", "forecast_soil_8hr"]),
            ],
        )

    def test_streamlit_refresh_seconds_uses_default_and_valid_env_value(self):
        self.assertEqual(streamlit_refresh_seconds({}), 10)
        self.assertEqual(streamlit_refresh_seconds({"STREAMLIT_REFRESH_SECONDS": "5"}), 5)

    def test_streamlit_refresh_seconds_disables_invalid_or_zero_value(self):
        self.assertEqual(streamlit_refresh_seconds({"STREAMLIT_REFRESH_SECONDS": "0"}), 0)
        self.assertEqual(streamlit_refresh_seconds({"STREAMLIT_REFRESH_SECONDS": "abc"}), 0)


if __name__ == "__main__":
    unittest.main()
