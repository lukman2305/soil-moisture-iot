import unittest

import pandas as pd

from streamlit_app import chart_sections


class StreamlitDashboardTest(unittest.TestCase):
    def test_chart_sections_keep_temperature_and_humidity_separate(self):
        frame = pd.DataFrame(
            {
                "timestamp": ["2026-06-14 10:00:00"],
                "soil_value": [45.0],
                "temperature": [32.0],
                "humidity": [55.0],
                "moisture_change_rate": [-5.0],
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
            ],
        )


if __name__ == "__main__":
    unittest.main()
