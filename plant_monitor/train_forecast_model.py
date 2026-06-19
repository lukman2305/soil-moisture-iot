import math
import os
from pathlib import Path

import pandas as pd

from plant_monitor.env import load_env_file
from plant_monitor.forecast import (
    FORECAST_FEATURE_COLUMNS,
    enrich_forecast_features,
    load_forecast_history,
    parse_forecast_horizons,
    save_forecast_model,
    train_forecast_model_from_frame,
)


BASE_DIR = Path(__file__).resolve().parents[1]


def parse_csv_paths(value, default_path):
    if value is None:
        return [Path(default_path)]
    paths = []
    for item in str(value).split(","):
        item = item.strip()
        if item:
            paths.append(Path(item))
    return paths or [Path(default_path)]


def load_training_frames(paths):
    frames = []
    loaded_paths = []
    for path in paths:
        if path.exists():
            frame = load_forecast_history(path)
            if not frame.empty:
                frames.append(frame)
                loaded_paths.append(path)
    if not frames:
        return None, []
    combined = pd.concat(frames, ignore_index=True)
    if "timestamp" in combined.columns:
        combined["timestamp"] = pd.to_datetime(combined["timestamp"], errors="coerce")
        combined = combined.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return combined, loaded_paths


def evaluate_accuracy(frame, min_rows, horizons, accuracy_path):
    if len(frame) < min_rows * 2:
        print("Not enough data to perform 80/20 accuracy evaluation split.")
        return

    train_size = int(len(frame) * 0.8)
    train_frame = frame.iloc[:train_size].copy()
    test_frame = frame.iloc[train_size:].copy()

    # Train eval model
    eval_bundle = train_forecast_model_from_frame(train_frame, min_rows=min_rows, horizons_hours=horizons)
    if not eval_bundle.is_ready:
        print("Evaluation model could not be trained.")
        return

    print("Evaluating model accuracy on unseen test data (20%)...")
    enriched_test = enrich_forecast_features(test_frame)
    usable_test = enriched_test.dropna(subset=["soil_value"])
    if usable_test.empty:
        print("Test set has no usable rows after enrichment.")
        return

    endog_test = usable_test["soil_value"].astype(float)
    exog_test = None
    if eval_bundle.feature_columns:
        usable_test = usable_test.dropna(subset=eval_bundle.feature_columns)
        if usable_test.empty:
            print("Test set missing exog features.")
            return
        endog_test = usable_test["soil_value"].astype(float)
        exog_test = usable_test[eval_bundle.feature_columns].astype(float)

    try:
        if exog_test is not None:
            res = eval_bundle.model.apply(endog_test, exog=exog_test)
        else:
            res = eval_bundle.model.apply(endog_test)
        
        preds = res.fittedvalues
        mae = (preds - endog_test).abs().mean()
        rmse = math.sqrt(((preds - endog_test) ** 2).mean())
        print(f"--> Test MAE: ±{mae:.2f}% moisture")
        print(f"--> Test RMSE: {rmse:.2f}%")
        
        import json
        with open(accuracy_path, "w") as f:
            json.dump({"mae": round(mae, 2), "rmse": round(rmse, 2)}, f)
            
    except Exception as e:
        print(f"Error evaluating accuracy: {e}")


def main():
    load_env_file(BASE_DIR / ".env")

    csv_file = Path(os.getenv("CSV_FILE", str(BASE_DIR / "plant_data.csv")))
    model_path = Path(os.getenv("FORECAST_MODEL_PATH", str(BASE_DIR / "models" / "soil_forecast_sarimax.joblib")))
    min_rows = int(os.getenv("FORECAST_MIN_ROWS", "24"))
    horizons = parse_forecast_horizons(os.getenv("FORECAST_HORIZONS_HOURS", "4,6,8"))
    training_csv_value = os.getenv("TRAINING_CSV_FILES", os.getenv("TRAINING_CSV_FILE", str(csv_file)))
    training_paths = parse_csv_paths(training_csv_value, csv_file)

    frame, loaded_paths = load_training_frames(training_paths)
    if frame is None:
        frame = load_forecast_history(csv_file)
        loaded_paths = [csv_file] if not frame.empty else []

    print(f"Training source: {', '.join(str(path) for path in loaded_paths) if loaded_paths else csv_file}")
    print(f"Rows loaded: {len(frame)}")

    accuracy_path = model_path.parent / "model_accuracy.json"
    evaluate_accuracy(frame, min_rows, horizons, accuracy_path)

    print("\nTraining final model on 100% of the data...")
    bundle = train_forecast_model_from_frame(frame, min_rows=min_rows, horizons_hours=horizons)
    print(f"Status: {bundle.status_code}")

    if not bundle.is_ready:
        print(f"Need at least {min_rows} usable time-series rows before SARIMAX can be trained.")
        return

    save_forecast_model(bundle, model_path)
    print(f"Saved forecast model: {model_path}")
    print(f"Usable training rows: {bundle.training_rows}")


if __name__ == "__main__":
    main()
