import unittest
from datetime import datetime, timedelta

import pandas as pd

from plant_monitor.forecast import (
    FORECAST_DRY,
    FORECAST_OK,
    ForecastResult,
    add_forecast_targets,
    calculate_vpd,
    classify_forecast_risk,
    enrich_forecast_features,
    forecast_recommendation,
    train_forecast_model_from_frame,
    recent_average_exog,
)


class ForecastTest(unittest.TestCase):
    def sample_frame(self):
        start = datetime(2026, 6, 12, 8, 0, 0)
        return pd.DataFrame(
            {
                "timestamp": [start + timedelta(hours=i) for i in range(9)],
                "temperature": [30, 31, 32, 33, 34, 35, 36, 37, 38],
                "humidity": [70, 68, 66, 64, 62, 60, 58, 56, 54],
                "soil_value": [70, 66, 61, 55, 48, 40, 31, 26, 22],
            }
        )

    def test_calculate_vpd_uses_temperature_and_humidity(self):
        self.assertAlmostEqual(calculate_vpd(30.0, 70.0), 1.273, places=3)
        self.assertIsNone(calculate_vpd(None, 70.0))
        self.assertIsNone(calculate_vpd(30.0, None))

    def test_enrich_forecast_features_adds_lags_rolling_mean_and_hourly_rate(self):
        enriched = enrich_forecast_features(self.sample_frame(), rolling_window=3)

        self.assertEqual(enriched.loc[3, "soil_lag_1"], 61.0)
        self.assertEqual(enriched.loc[3, "soil_lag_2"], 66.0)
        self.assertEqual(enriched.loc[3, "soil_lag_3"], 70.0)
        self.assertEqual(enriched.loc[3, "soil_rolling_mean"], 60.7)
        self.assertEqual(enriched.loc[3, "soil_rate_per_hour"], -6.0)
        self.assertGreater(enriched.loc[3, "vpd"], 0)

    def test_add_forecast_targets_uses_timestamp_horizons(self):
        targeted = add_forecast_targets(self.sample_frame(), horizons_hours=[4, 6, 8])

        self.assertEqual(targeted.loc[0, "target_soil_4hr"], 48.0)
        self.assertEqual(targeted.loc[0, "target_soil_6hr"], 31.0)
        self.assertEqual(targeted.loc[0, "target_soil_8hr"], 22.0)
        self.assertTrue(pd.isna(targeted.loc[7, "target_soil_4hr"]))

    def test_recent_average_exog_uses_recent_window(self):
        enriched = enrich_forecast_features(self.sample_frame(), rolling_window=3)

        averages = recent_average_exog(enriched, recent_average_hours=2)

        self.assertAlmostEqual(averages["temperature"], 37.0)
        self.assertAlmostEqual(averages["humidity"], 56.0)
        self.assertAlmostEqual(averages["soil_lag_1"], 32.333, places=3)
        self.assertIn("vpd", averages)

    def test_classify_forecast_risk_marks_any_horizon_below_threshold_dry(self):
        result = classify_forecast_risk(
            {"forecast_soil_4hr": 34.0, "forecast_soil_6hr": 28.0, "forecast_soil_8hr": 40.0},
            dry_threshold=30.0,
        )

        self.assertEqual(result.forecast_risk, "Dry Forecast")
        self.assertEqual(result.ml_prediction, FORECAST_DRY)

    def test_classify_forecast_risk_marks_safe_forecast_ok(self):
        result = classify_forecast_risk(
            {"forecast_soil_4hr": 44.0, "forecast_soil_6hr": 38.0, "forecast_soil_8hr": 31.0},
            dry_threshold=30.0,
        )

        self.assertEqual(result.forecast_risk, "OK")
        self.assertEqual(result.ml_prediction, FORECAST_OK)

    def test_forecast_recommendation_explains_recommend_and_control_mode(self):
        dry = ForecastResult(forecast_soil_4hr=28.0, forecast_risk="Dry Forecast")
        ok = ForecastResult(forecast_soil_4hr=44.0, forecast_risk="OK")

        self.assertIn("Recommend watering", forecast_recommendation(dry, "recommend"))
        self.assertIn("Pump may turn ON early", forecast_recommendation(dry, "control"))
        self.assertEqual(forecast_recommendation(ok, "recommend"), "Forecast OK. No early watering needed.")

    def test_train_forecast_model_from_frame_falls_back_for_small_constant_data(self):
        frame = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-06-14 00:00:00", periods=4, freq="H"),
                "temperature": [32.0, 32.0, 32.0, 32.0],
                "humidity": [55.0, 55.0, 55.0, 55.0],
                "soil_value": [45.0, 45.0, 45.0, 45.0],
            }
        )

        bundle = train_forecast_model_from_frame(frame, min_rows=4, horizons_hours=[4, 6, 8])

        self.assertTrue(bundle.is_ready)
        self.assertEqual(bundle.training_rows, 4)
        self.assertEqual(bundle.status_code, "FORECAST_MODEL_TRAINED")


if __name__ == "__main__":
    unittest.main()
