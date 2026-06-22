import os
from pathlib import Path
from plant_monitor.forecast import load_or_train_forecast_model

# Ensure models directory exists
Path("models").mkdir(exist_ok=True)

print("Reading history and training SARIMAX model...")
print("This may take 30-60 seconds depending on how much history you have.")

bundle = load_or_train_forecast_model(
    model_path="models/soil_forecast_sarimax.joblib",
    training_csv_path="plant_data.csv",
    min_rows=24
)

print(f"Result: {bundle.status_code}")
if bundle.is_ready:
    print("Success! Model is fully trained and saved to models/soil_forecast_sarimax.joblib")
else:
    print("Failed to train. Make sure you have enough data in plant_data.csv.")
