import sys
import pandas as pd
from plant_monitor.forecast import enrich_forecast_features

def backfill(csv_file):
    df = pd.read_csv(csv_file)
    
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp")

    df = enrich_forecast_features(df)

    if "soil_value" in df.columns and "soil_lag_1" in df.columns:
        df["previous_soil_value"] = df["soil_lag_1"]
        df["moisture_change_rate"] = df["soil_value"] - df["soil_lag_1"]
        df["moisture_change_rate"] = df["moisture_change_rate"].fillna(0.0)
        df["previous_soil_value"] = df["previous_soil_value"].fillna(df["soil_value"])

    for col in ["moisture_change_rate", "previous_soil_value", "soil_lag_1", "soil_lag_2", "soil_lag_3", "soil_rolling_mean", "soil_rate_per_hour"]:
        if col in df.columns:
            df[col] = df[col].round(1)

    df.to_csv(csv_file, index=False)
    print(f"Backfilled {csv_file} successfully.")

if __name__ == "__main__":
    files = sys.argv[1:] if len(sys.argv) > 1 else ["plant_data.csv"]
    for f in files:
        backfill(f)
