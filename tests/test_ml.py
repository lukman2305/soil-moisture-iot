import tempfile
import unittest
from pathlib import Path

from plant_monitor.ml import (
    DRY_SOON,
    NOT_DRY_SOON,
    calculate_moisture_change_rate,
    load_or_train_model,
    normalize_training_frame,
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

    def test_load_or_train_model_uses_kaggle_training_csv_when_available(self):
        with tempfile.TemporaryDirectory() as directory:
            training_path = Path(directory) / "training.csv"
            training_path.write_text(
                "\n".join(
                    [
                        "crop ID,soil_type,Seedling Stage,MOI,temp,humidity,result",
                        "Wheat,Black Soil,Germination,20,35,45,1",
                        "Wheat,Black Soil,Germination,35,34,55,2",
                        "Wheat,Black Soil,Germination,75,25,85,0",
                        "Corn,Red Soil,Growth,18,36,40,1",
                        "Corn,Red Soil,Growth,72,26,82,0",
                    ]
                ),
                encoding="utf-8",
            )

            model_bundle = load_or_train_model(model_path=None, training_csv_path=training_path)

        self.assertEqual(model_bundle.status_code, "MODEL_TRAINED_FROM_CSV")
        self.assertEqual(model_bundle.labels, [DRY_SOON, NOT_DRY_SOON])

    def test_normalize_training_frame_supports_kaggle_smart_agriculture_schema(self):
        import pandas as pd

        kaggle_frame = pd.DataFrame(
            {
                "crop ID": ["Wheat", "Wheat", "Wheat"],
                "soil_type": ["Black Soil", "Black Soil", "Black Soil"],
                "Seedling Stage": ["Germination", "Germination", "Germination"],
                "MOI": [20, 35, 75],
                "temp": [35, 34, 25],
                "humidity": [45.0, 55.0, 85.0],
                "result": [1, 2, 0],
            }
        )

        normalized = normalize_training_frame(kaggle_frame)

        self.assertEqual(normalized["soil_value"].tolist(), [20.0, 35.0, 75.0])
        self.assertEqual(normalized["temperature"].tolist(), [35.0, 34.0, 25.0])
        self.assertEqual(normalized["dry_soon_label"].tolist(), [DRY_SOON, DRY_SOON, NOT_DRY_SOON])
        self.assertEqual(normalized["previous_soil_value"].tolist(), [20.0, 20.0, 35.0])
        self.assertEqual(normalized["moisture_change_rate"].tolist(), [0.0, 15.0, 40.0])
        self.assertEqual(normalized["pump_status_code"].tolist(), [1, 0, 0])

    def test_normalize_training_frame_derives_labels_from_next_real_soil_reading(self):
        import pandas as pd

        real_frame = pd.DataFrame(
            {
                "timestamp": [
                    "2026-06-13 10:00:00",
                    "2026-06-13 10:10:00",
                    "2026-06-13 10:20:00",
                ],
                "temperature": [34.0, 33.0, 28.0],
                "humidity": [48.0, 50.0, 80.0],
                "soil_value": [36.0, 28.0, 62.0],
                "previous_soil_value": [44.0, 36.0, 28.0],
                "moisture_change_rate": [-8.0, -8.0, 34.0],
                "pump_status": ["OFF", "ON", "OFF"],
                "dry_soon_label": ["", "", ""],
            }
        )

        normalized = normalize_training_frame(real_frame)

        self.assertEqual(normalized["soil_value"].tolist(), [36.0, 28.0])
        self.assertEqual(normalized["dry_soon_label"].tolist(), [DRY_SOON, NOT_DRY_SOON])
        self.assertEqual(normalized["pump_status_code"].tolist(), [0, 1])


if __name__ == "__main__":
    unittest.main()
