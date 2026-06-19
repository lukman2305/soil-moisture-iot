# Training Data

Place the Kaggle or real Raspberry Pi training CSV here when it is available.

The first supported training file path is:

```text
data/training_smart_agriculture.csv
```

The uploaded Kaggle smart agriculture CSV can be used directly with these raw columns:

```text
crop ID,soil_type,Seedling Stage,MOI,temp,humidity,result
```

The project maps `MOI` to `soil_value`, `temp` to `temperature`, and `result` to the `Dry Soon` / `Not Dry Soon` label. For this project, `result=0` is treated as `Not Dry Soon`, while `result=1` and `result=2` are treated as `Dry Soon`.

The canonical project training columns are also supported:

```text
soil_value,temperature,humidity,previous_soil_value,moisture_change_rate,pump_status,dry_soon_label
```

`dry_soon_label` should be either:

```text
Dry Soon
Not Dry Soon
```

If the CSV is missing, the system uses a small bootstrap demo dataset so the dashboard and Raspberry Pi script can still run.

Later, after enough real readings are collected in `plant_data.csv`, set this in `.env` to retrain from real sensor data:

```bash
TRAINING_CSV_FILE=plant_data.csv
```

If real `plant_data.csv` rows have a blank `dry_soon_label`, the trainer creates labels from the next soil reading. With the default 10-minute sampling interval, that means it learns whether the soil becomes dry in the next 10 minutes.
