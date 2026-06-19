from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.tree import DecisionTreeClassifier


DRY_SOON = "Dry Soon"
NOT_DRY_SOON = "Not Dry Soon"
UNKNOWN = "Unknown"
FEATURE_COLUMNS = [
    "soil_value",
    "temperature",
    "humidity",
    "previous_soil_value",
    "moisture_change_rate",
    "pump_status_code",
]
LABEL_COLUMN = "dry_soon_label"
KAGGLE_REQUIRED_COLUMNS = ["MOI", "temp", "humidity", "result"]
KAGGLE_GROUP_COLUMNS = ["crop ID", "soil_type", "Seedling Stage"]
DEFAULT_DRY_PERCENT = 30.0


@dataclass
class ModelBundle:
    model: DecisionTreeClassifier
    labels: list
    status_code: str


def calculate_moisture_change_rate(soil_value, previous_soil_value):
    if previous_soil_value is None:
        return 0.0
    return round(float(soil_value) - float(previous_soil_value), 1)


def pump_status_code(pump_status):
    return 1 if pump_status == "ON" else 0


def bootstrap_training_frame():
    rows = [
        # Hot, low humidity, falling moisture: dry soon.
        [42, 35, 45, 50, -8, 0, DRY_SOON],
        [35, 33, 50, 43, -8, 0, DRY_SOON],
        [28, 30, 70, 32, -4, 1, DRY_SOON],
        [45, 36, 42, 53, -8, 0, DRY_SOON],
        # Stable or humid conditions: not dry soon.
        [62, 25, 85, 63, -1, 0, NOT_DRY_SOON],
        [70, 28, 80, 71, -1, 0, NOT_DRY_SOON],
        [55, 27, 75, 56, -1, 0, NOT_DRY_SOON],
        [50, 25, 82, 50, 0, 0, NOT_DRY_SOON],
        [80, 30, 60, 81, -1, 0, NOT_DRY_SOON],
    ]
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS + [LABEL_COLUMN])


def _has_kaggle_schema(frame):
    return all(column in frame.columns for column in KAGGLE_REQUIRED_COLUMNS)


def _normalize_kaggle_frame(frame):
    source = frame.copy()
    source["soil_value"] = pd.to_numeric(source["MOI"], errors="coerce")
    source["temperature"] = pd.to_numeric(source["temp"], errors="coerce")
    source["humidity"] = pd.to_numeric(source["humidity"], errors="coerce")

    group_columns = [column for column in KAGGLE_GROUP_COLUMNS if column in source.columns]
    if group_columns:
        previous_soil = source.groupby(group_columns)["soil_value"].shift(1)
    else:
        previous_soil = source["soil_value"].shift(1)

    normalized = pd.DataFrame()
    normalized["soil_value"] = source["soil_value"]
    normalized["temperature"] = source["temperature"]
    normalized["humidity"] = source["humidity"]
    normalized["previous_soil_value"] = previous_soil.fillna(source["soil_value"])
    normalized["moisture_change_rate"] = (
        normalized["soil_value"] - normalized["previous_soil_value"]
    ).round(1)
    normalized["pump_status_code"] = (normalized["soil_value"] < 30).astype(int)
    normalized[LABEL_COLUMN] = pd.to_numeric(source["result"], errors="coerce").map(
        {
            0: NOT_DRY_SOON,
            1: DRY_SOON,
            2: DRY_SOON,
        }
    )
    return normalized[FEATURE_COLUMNS + [LABEL_COLUMN]].dropna()


def _labels_are_empty(normalized):
    if LABEL_COLUMN not in normalized.columns:
        return True
    labels = normalized[LABEL_COLUMN].astype("string").fillna("").str.strip()
    return labels.eq("").all()


def _derive_next_sample_labels(normalized):
    if "soil_value" not in normalized.columns:
        return normalized

    if "timestamp" in normalized.columns:
        normalized = normalized.sort_values("timestamp").reset_index(drop=True)

    soil_value = pd.to_numeric(normalized["soil_value"], errors="coerce")
    future_soil_value = soil_value.shift(-1)
    normalized[LABEL_COLUMN] = future_soil_value.apply(_future_soil_label)
    return normalized


def _future_soil_label(value):
    if pd.isna(value):
        return pd.NA
    return DRY_SOON if value < DEFAULT_DRY_PERCENT else NOT_DRY_SOON


def _derive_missing_trend_features(normalized):
    if "soil_value" not in normalized.columns:
        return normalized

    soil_value = pd.to_numeric(normalized["soil_value"], errors="coerce")
    if "previous_soil_value" not in normalized.columns:
        normalized["previous_soil_value"] = soil_value.shift(1).fillna(soil_value)
    if "moisture_change_rate" not in normalized.columns:
        previous_soil_value = pd.to_numeric(
            normalized["previous_soil_value"],
            errors="coerce",
        )
        normalized["moisture_change_rate"] = (soil_value - previous_soil_value).round(1)
    return normalized


def normalize_training_frame(frame):
    if _has_kaggle_schema(frame):
        return _normalize_kaggle_frame(frame)

    normalized = frame.copy()
    normalized = _derive_missing_trend_features(normalized)
    if _labels_are_empty(normalized):
        normalized = _derive_next_sample_labels(normalized)

    if "pump_status" in normalized.columns and "pump_status_code" not in normalized.columns:
        normalized["pump_status_code"] = normalized["pump_status"].map({"ON": 1, "OFF": 0}).fillna(0)

    missing = [column for column in FEATURE_COLUMNS + [LABEL_COLUMN] if column not in normalized.columns]
    if missing:
        raise ValueError("Training data missing columns: " + ", ".join(missing))

    for column in FEATURE_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized[LABEL_COLUMN] = normalized[LABEL_COLUMN].astype("string").str.strip()

    return normalized[FEATURE_COLUMNS + [LABEL_COLUMN]].dropna()


def _train_from_frame(frame, status_code):
    training = normalize_training_frame(frame)
    model = DecisionTreeClassifier(max_depth=4, random_state=42)
    model.fit(training[FEATURE_COLUMNS], training[LABEL_COLUMN])
    labels = sorted(training[LABEL_COLUMN].unique().tolist())
    return ModelBundle(model=model, labels=labels, status_code=status_code)


def load_or_train_model(model_path=None, training_csv_path=None):
    if model_path:
        path = Path(model_path)
        if path.exists():
            bundle = joblib.load(path)
            bundle.status_code = "MODEL_LOADED"
            return bundle

    if training_csv_path:
        path = Path(training_csv_path)
        if path.exists():
            return _train_from_frame(pd.read_csv(path), "MODEL_TRAINED_FROM_CSV")

    return _train_from_frame(bootstrap_training_frame(), "MODEL_BOOTSTRAP_USED")


def feature_row(soil_value, temperature, humidity, previous_soil_value, moisture_change_rate, pump_status):
    return {
        "soil_value": float(soil_value),
        "temperature": float(temperature),
        "humidity": float(humidity),
        "previous_soil_value": float(previous_soil_value if previous_soil_value is not None else soil_value),
        "moisture_change_rate": float(moisture_change_rate),
        "pump_status_code": pump_status_code(pump_status),
    }


def predict_dryness(
    model_bundle,
    soil_value,
    temperature,
    humidity,
    previous_soil_value,
    moisture_change_rate,
    pump_status,
):
    if soil_value is None or temperature is None or humidity is None:
        return UNKNOWN

    frame = pd.DataFrame(
        [
            feature_row(
                soil_value,
                temperature,
                humidity,
                previous_soil_value,
                moisture_change_rate,
                pump_status,
            )
        ],
        columns=FEATURE_COLUMNS,
    )
    return str(model_bundle.model.predict(frame)[0])


def save_model(model_bundle, model_path):
    path = Path(model_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model_bundle, path)
