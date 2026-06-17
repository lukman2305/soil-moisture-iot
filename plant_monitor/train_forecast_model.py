import os
from pathlib import Path

import pandas as pd

from plant_monitor.env import load_env_file
from plant_monitor.forecast import (
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

    bundle = train_forecast_model_from_frame(frame, min_rows=min_rows, horizons_hours=horizons)

    print(f"Training source: {', '.join(str(path) for path in loaded_paths) if loaded_paths else csv_file}")
    print(f"Rows loaded: {len(frame)}")
    print(f"Status: {bundle.status_code}")

    if not bundle.is_ready:
        print(f"Need at least {min_rows} usable time-series rows before SARIMAX can be trained.")
        return

    save_forecast_model(bundle, model_path)
    print(f"Saved forecast model: {model_path}")
    print(f"Usable training rows: {bundle.training_rows}")


if __name__ == "__main__":
    main()
