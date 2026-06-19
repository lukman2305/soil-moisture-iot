import pandas as pd
from plant_monitor.forecast import enrich_forecast_features

def backfill():
    df = pd.read_csv("plant_data.csv")
    
    # Sort and ensure timestamp is parsed
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp")

    # Use existing enrichment logic to backfill lags and rolling means
    df = enrich_forecast_features(df)

    # Backfill moisture_change_rate
    if "soil_value" in df.columns and "soil_lag_1" in df.columns:
        df["previous_soil_value"] = df["soil_lag_1"]
        df["moisture_change_rate"] = df["soil_value"] - df["soil_lag_1"]
        # Fill first row where lag is NaN with 0
        df["moisture_change_rate"] = df["moisture_change_rate"].fillna(0.0)
        df["previous_soil_value"] = df["previous_soil_value"].fillna(df["soil_value"])

    # Round to 1 decimal place to keep CSV clean
    for col in ["moisture_change_rate", "previous_soil_value", "soil_lag_1", "soil_lag_2", "soil_lag_3", "soil_rolling_mean", "soil_rate_per_hour"]:
        if col in df.columns:
            df[col] = df[col].round(1)

    df.to_csv("plant_data.csv", index=False)
    print("Backfilled plant_data.csv successfully.")

if __name__ == "__main__":
    backfill()
