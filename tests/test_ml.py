import tempfile
import unittest
from pathlib import Path

from plant_monitor.ml import (
    DRY_SOON,
    NOT_DRY_SOON,
    calculate_moisture_change_rate,
    load_or_train_model,
    predict_dryness,
)


class MachineLearningTest(unittest.TestCase):
    def test_calculate_moisture_change_rate_defaults_to_zero_without_previous_value(self):
        self.assertEqual(calculate_moisture_change_rate(45.0, None), 0.0)
        self.assertEqual(calculate_moisture_change_rate(37.5, 45.0), -7.5)

    def test_bootstrap_model_predicts_dry_soon_for_hot_low_humidity_falling_soil(self):
        model_bundle = load_or_train_model(model_path=None, training_csv_path=None)

        prediction = predict_dryness(
            model_bundle,
            soil_value=42.0,
            temperature=35.0,
            humidity=45.0,
            previous_soil_value=50.0,
            moisture_change_rate=-8.0,
            pump_status="OFF",
        )

        self.assertEqual(prediction, DRY_SOON)
        self.assertEqual(model_bundle.status_code, "MODEL_BOOTSTRAP_USED")

    def test_predict_dryness_returns_unknown_when_sensor_data_is_missing(self):
        model_bundle = load_or_train_model(model_path=None, training_csv_path=None)

        prediction = predict_dryness(
            model_bundle,
            soil_value=42.0,
            temperature=None,
            humidity=45.0,
            previous_soil_value=50.0,
            moisture_change_rate=-8.0,
            pump_status="OFF",
        )

        self.assertEqual(prediction, "Unknown")

    def test_load_or_train_model_uses_canonical_training_csv_when_available(self):
        with tempfile.TemporaryDirectory() as directory:
            training_path = Path(directory) / "training.csv"
            training_path.write_text(
                "\n".join(
                    [
                        "soil_value,temperature,humidity,previous_soil_value,moisture_change_rate,pump_status,dry_soon_label",
                        "42,35,45,50,-8,OFF,Dry Soon",
                        "62,25,85,63,-1,OFF,Not Dry Soon",
                        "24,30,70,25,-1,ON,Dry Soon",
                        "70,28,80,71,-1,OFF,Not Dry Soon",
                    ]
                ),
                encoding="utf-8",
            )

            model_bundle = load_or_train_model(model_path=None, training_csv_path=training_path)

        self.assertEqual(model_bundle.status_code, "MODEL_TRAINED_FROM_CSV")
        self.assertEqual(model_bundle.labels, [DRY_SOON, NOT_DRY_SOON])


if __name__ == "__main__":
    unittest.main()
