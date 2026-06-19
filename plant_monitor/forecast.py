from dataclasses import dataclass, field
from datetime import timedelta
from math import ceil, exp
from pathlib import Path

import joblib
import pandas as pd


FORECAST_DRY = "Forecast Dry"
FORECAST_OK = "Forecast OK"
FORECAST_UNKNOWN = "Unknown"
FORECAST_RISK_DRY = "Dry Forecast"
FORECAST_RISK_OK = "OK"
FORECAST_NOT_ENOUGH_DATA = "FORECAST_NOT_ENOUGH_DATA"
FORECAST_MODEL_MISSING = "FORECAST_MODEL_MISSING"
FORECAST_MODEL_LOADED = "FORECAST_MODEL_LOADED"
FORECAST_MODEL_TRAINED = "FORECAST_MODEL_TRAINED"
FORECAST_UNAVAILABLE = "FORECAST_UNAVAILABLE"

FORECAST_FEATURE_COLUMNS = [
    "temperature",
    "humidity",
    "vpd",
    "soil_lag_1",
    "soil_lag_2",
    "soil_lag_3",
    "soil_rolling_mean",
    "soil_rate_per_hour",
]

DEFAULT_FORECAST_HORIZONS = [4, 6, 8]


@dataclass
class ForecastBundle:
    model: object = None
    status_code: str = FORECAST_MODEL_MISSING
    feature_columns: list[str] = field(default_factory=lambda: list(FORECAST_FEATURE_COLUMNS))
    frequency_minutes: float = 10.0
    training_rows: int = 0

    @property
    def is_ready(self):
        return self.model is not None


@dataclass
class ForecastResult:
    forecast_soil_4hr: float | None = None
    forecast_soil_6hr: float | None = None
    forecast_soil_8hr: float | None = None
    forecast_risk: str = FORECAST_UNKNOWN
    forecast_recommendation: str = "Forecast unavailable."
    ml_prediction: str = FORECAST_UNKNOWN
    status_code: str = FORECAST_UNAVAILABLE

    def values(self):
        return {
            "forecast_soil_4hr": self.forecast_soil_4hr,
            "forecast_soil_6hr": self.forecast_soil_6hr,
            "forecast_soil_8hr": self.forecast_soil_8hr,
        }


def horizon_column(prefix, horizon_hours):
    horizon = int(horizon_hours) if float(horizon_hours).is_integer() else horizon_hours
    return f"{prefix}_{horizon}hr"


def parse_forecast_horizons(value):
    if isinstance(value, (list, tuple)):
        return [int(item) for item in value]
    horizons = []
    for item in str(value).split(","):
        item = item.strip()
        if item:
            horizons.append(int(float(item)))
    return horizons or list(DEFAULT_FORECAST_HORIZONS)


def calculate_vpd(temperature, humidity):
    if temperature is None or humidity is None or pd.isna(temperature) or pd.isna(humidity):
        return None
    humidity = max(0.0, min(100.0, float(humidity)))
    saturation_vapour_pressure = 0.6108 * exp((17.27 * float(temperature)) / (float(temperature) + 237.3))
    actual_vapour_pressure = saturation_vapour_pressure * (humidity / 100.0)
    return round(max(0.0, saturation_vapour_pressure - actual_vapour_pressure), 3)


def _prepare_frame(frame):
    if frame is None or len(frame) == 0:
        return pd.DataFrame()
    prepared = frame.copy()
    if "timestamp" in prepared.columns:
        prepared["timestamp"] = pd.to_datetime(prepared["timestamp"], errors="coerce")
    else:
        prepared["timestamp"] = pd.NaT
    for column in ["temperature", "humidity", "soil_value"]:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
        else:
            prepared[column] = pd.NA
    return prepared.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)


def enrich_forecast_features(frame, rolling_window=3):
    enriched = _prepare_frame(frame)
    if enriched.empty:
        return enriched

    enriched["vpd"] = [
        calculate_vpd(temperature, humidity)
        for temperature, humidity in zip(enriched["temperature"], enriched["humidity"])
    ]
    for lag in (1, 2, 3):
        enriched[f"soil_lag_{lag}"] = enriched["soil_value"].shift(lag)

    enriched["soil_rolling_mean"] = (
        enriched["soil_value"].rolling(window=rolling_window, min_periods=1).mean().round(1)
    )
    elapsed_hours = enriched["timestamp"].diff().dt.total_seconds() / 3600.0
    elapsed_hours = elapsed_hours.replace(0, pd.NA)
    enriched["soil_rate_per_hour"] = (enriched["soil_value"].diff() / elapsed_hours).fillna(0.0).round(3)
    return enriched


def add_forecast_targets(frame, horizons_hours=None):
    horizons = horizons_hours or DEFAULT_FORECAST_HORIZONS
    targeted = _prepare_frame(frame)
    if targeted.empty:
        return targeted

    timestamps = targeted["timestamp"]
    soil_values = targeted["soil_value"]
    for horizon in horizons:
        targets = []
        for timestamp in timestamps:
            target_time = timestamp + timedelta(hours=float(horizon))
            index = timestamps.searchsorted(target_time, side="left")
            targets.append(soil_values.iloc[index] if index < len(targeted) else pd.NA)
        targeted[horizon_column("target_soil", horizon)] = targets
    return targeted


def infer_frequency_minutes(frame, default=10.0):
    prepared = _prepare_frame(frame)
    if len(prepared) < 2:
        return float(default)
    differences = prepared["timestamp"].diff().dt.total_seconds().dropna()
    differences = differences[differences > 0]
    if differences.empty:
        return float(default)
    return max(float(differences.median()) / 60.0, 1.0)


def recent_average_exog(enriched_frame, recent_average_hours=1, feature_columns=None):
    feature_columns = feature_columns or FORECAST_FEATURE_COLUMNS
    frame = _prepare_frame(enriched_frame)
    if frame.empty:
        return {column: 0.0 for column in feature_columns}

    for column in feature_columns:
        if column not in frame.columns:
            frame[column] = pd.NA
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    latest_time = frame["timestamp"].max()
    cutoff = latest_time - timedelta(hours=float(recent_average_hours))
    recent = frame[frame["timestamp"] >= cutoff]
    if recent.empty:
        recent = frame.tail(1)

    averages = {}
    latest = frame.iloc[-1]
    for column in feature_columns:
        value = recent[column].mean(skipna=True)
        if pd.isna(value):
            value = latest[column]
        averages[column] = 0.0 if pd.isna(value) else round(float(value), 3)
    return averages


def forecast_recommendation(result, control_mode="recommend"):
    if result.forecast_risk == FORECAST_RISK_DRY:
        if control_mode == "control":
            return "Forecast dry. Pump may turn ON early because ML_CONTROL_MODE=control."
        return "Forecast dry. Recommend watering soon; pump stays OFF because ML_CONTROL_MODE=recommend."
    if result.forecast_risk == FORECAST_RISK_OK:
        return "Forecast OK. No early watering needed."
    return "Forecast unavailable. Using current soil threshold only."


def classify_forecast_risk(forecasts, dry_threshold=30.0, control_mode="recommend", status_code="OK"):
    values = {}
    valid_values = []
    for column in [horizon_column("forecast_soil", horizon) for horizon in DEFAULT_FORECAST_HORIZONS]:
        value = forecasts.get(column)
        if value is None or pd.isna(value):
            values[column] = None
            continue
        value = round(max(0.0, min(100.0, float(value))), 1)
        values[column] = value
        valid_values.append(value)

    if not valid_values:
        result = ForecastResult(**values, status_code=status_code or FORECAST_UNAVAILABLE)
        result.forecast_recommendation = forecast_recommendation(result, control_mode)
        return result

    is_dry = any(value < float(dry_threshold) for value in valid_values)
    result = ForecastResult(
        **values,
        forecast_risk=FORECAST_RISK_DRY if is_dry else FORECAST_RISK_OK,
        ml_prediction=FORECAST_DRY if is_dry else FORECAST_OK,
        status_code=status_code,
    )
    result.forecast_recommendation = forecast_recommendation(result, control_mode)
    return result


def load_forecast_history(csv_path):
    path = Path(csv_path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def append_current_reading(history_frame, timestamp, temperature, humidity, soil_value):
    current = pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "temperature": temperature,
                "humidity": humidity,
                "soil_value": soil_value,
            }
        ]
    )
    if history_frame is None or history_frame.empty:
        return current
    available = [column for column in ["timestamp", "temperature", "humidity", "soil_value"] if column in history_frame]
    return pd.concat([history_frame[available], current], ignore_index=True)


def train_forecast_model_from_frame(frame, min_rows=24, horizons_hours=None):
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    horizons = horizons_hours or DEFAULT_FORECAST_HORIZONS
    enriched = enrich_forecast_features(frame)
    targeted = add_forecast_targets(enriched, horizons)
    usable_frame = targeted.dropna(subset=["soil_value"])
    if len(usable_frame) < int(min_rows):
        return ForecastBundle(status_code=FORECAST_NOT_ENOUGH_DATA, training_rows=len(usable_frame))

    exog_frame = usable_frame.dropna(subset=FORECAST_FEATURE_COLUMNS)
    training_candidates = []
    if len(exog_frame) >= int(min_rows):
        training_candidates.append((exog_frame, True))
    training_candidates.append((usable_frame, False))

    for train_frame, use_exog in training_candidates:
        endog = train_frame["soil_value"].astype(float)
        try:
            if use_exog:
                exog = train_frame[FORECAST_FEATURE_COLUMNS].astype(float)
                model = SARIMAX(
                    endog,
                    exog=exog,
                    order=(1, 0, 0),
                    trend="c",
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False)
                feature_columns = list(FORECAST_FEATURE_COLUMNS)
            else:
                model = SARIMAX(
                    endog,
                    order=(1, 0, 0),
                    trend="n",
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False)
                feature_columns = []
            return ForecastBundle(
                model=model,
                status_code=FORECAST_MODEL_TRAINED,
                feature_columns=feature_columns,
                frequency_minutes=infer_frequency_minutes(train_frame),
                training_rows=len(train_frame),
            )
        except Exception:
            continue

    return ForecastBundle(status_code=FORECAST_UNAVAILABLE, training_rows=len(usable_frame))


def save_forecast_model(bundle, model_path):
    path = Path(model_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)


def load_forecast_model(model_path):
    path = Path(model_path)
    if not path.exists():
        return ForecastBundle(status_code=FORECAST_MODEL_MISSING)
    bundle = joblib.load(path)
    if isinstance(bundle, ForecastBundle):
        bundle.status_code = FORECAST_MODEL_LOADED
        return bundle
    return ForecastBundle(model=bundle, status_code=FORECAST_MODEL_LOADED)


def load_or_train_forecast_model(model_path, training_csv_path, min_rows=24, horizons_hours=None):
    path = Path(model_path)
    if path.exists():
        return load_forecast_model(path)

    frame = load_forecast_history(training_csv_path)
    bundle = train_forecast_model_from_frame(frame, min_rows=min_rows, horizons_hours=horizons_hours)
    if bundle.is_ready:
        save_forecast_model(bundle, path)
    return bundle


def forecast_soil_moisture(
    bundle,
    history_frame,
    horizons_hours=None,
    recent_average_hours=1,
    dry_threshold=30.0,
    control_mode="recommend",
):
    horizons = horizons_hours or DEFAULT_FORECAST_HORIZONS
    if bundle is None or not bundle.is_ready:
        status = bundle.status_code if bundle else FORECAST_MODEL_MISSING
        return classify_forecast_risk({}, dry_threshold, control_mode, status)

    enriched = enrich_forecast_features(history_frame)
    if len(enriched.dropna(subset=["soil_value"])) < 2:
        return classify_forecast_risk({}, dry_threshold, control_mode, FORECAST_NOT_ENOUGH_DATA)

    frequency_minutes = infer_frequency_minutes(enriched, default=bundle.frequency_minutes)
    max_steps = max(1, int(ceil(max(horizons) * 60.0 / frequency_minutes)))
    averages = recent_average_exog(
        enriched,
        recent_average_hours=recent_average_hours,
        feature_columns=bundle.feature_columns,
    )
    future_exog = pd.DataFrame([averages for _ in range(max_steps)], columns=bundle.feature_columns)

    model = bundle.model
    model_exog = getattr(getattr(model, "model", None), "exog", None)
    try:
        if model_exog is None:
            predictions = model.forecast(steps=max_steps)
        else:
            predictions = model.forecast(steps=max_steps, exog=future_exog)
    except Exception:
        return classify_forecast_risk({}, dry_threshold, control_mode, FORECAST_UNAVAILABLE)

    forecasts = {}
    for horizon in horizons:
        step = max(1, int(ceil(float(horizon) * 60.0 / frequency_minutes)))
        step = min(step, len(predictions))
        forecasts[horizon_column("forecast_soil", horizon)] = predictions.iloc[step - 1]
    return classify_forecast_risk(forecasts, dry_threshold, control_mode, "OK")
