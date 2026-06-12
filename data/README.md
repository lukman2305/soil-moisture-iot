# Training Data

Place the Kaggle or real Raspberry Pi training CSV here when it is available.

The first supported training file path is:

```text
data/training_smart_agriculture.csv
```

For automatic model training, use these canonical columns:

```text
soil_value,temperature,humidity,previous_soil_value,moisture_change_rate,pump_status,dry_soon_label
```

`dry_soon_label` should be either:

```text
Dry Soon
Not Dry Soon
```

If the CSV is missing, the system uses a small bootstrap demo dataset so the dashboard and Raspberry Pi script can still run.
