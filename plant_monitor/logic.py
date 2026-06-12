import os
from dataclasses import dataclass


DEFAULT_FAVORIOT_URL = "https://apiv2.favoriot.com/v2/streams"
PLACEHOLDER_VALUES = {
    "PASTE_YOUR_NEW_API_KEY_HERE",
    "PASTE_YOUR_DEVICE_DEVELOPER_ID_HERE",
    "CHANGE_ME",
}


@dataclass(frozen=True)
class FavoriotConfig:
    api_key: str
    device_developer_id: str
    url: str = DEFAULT_FAVORIOT_URL

    @property
    def is_configured(self):
        values = [self.api_key.strip(), self.device_developer_id.strip()]
        return all(values) and not any(value in PLACEHOLDER_VALUES for value in values)


def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, value))


def raw_to_moisture_percent(raw_value, dry_raw=1.0, wet_raw=0.0):
    """Convert MCP3008 0..1 reading to 0..100 where 100 means wet."""
    if dry_raw == wet_raw:
        raise ValueError("dry_raw and wet_raw must be different calibration values")

    percentage = ((raw_value - dry_raw) / (wet_raw - dry_raw)) * 100.0
    return round(clamp(percentage), 1)


def classify_soil(soil_value, dry_threshold=30.0, wet_threshold=70.0):
    if dry_threshold >= wet_threshold:
        raise ValueError("dry_threshold must be lower than wet_threshold")

    if soil_value < dry_threshold:
        return "DRY"
    if soil_value > wet_threshold:
        return "WET"
    return "OPTIMAL"


def decide_pump_status(soil_status):
    return "ON" if soil_status == "DRY" else "OFF"


def decide_pump_status_with_ml(soil_status, ml_prediction, control_mode="recommend"):
    if soil_status == "DRY":
        return "ON"
    if soil_status == "WET":
        return "OFF"
    if control_mode == "control" and soil_status == "OPTIMAL" and ml_prediction == "Dry Soon":
        return "ON"
    return "OFF"


def load_favoriot_config(env=None):
    source = os.environ if env is None else env
    return FavoriotConfig(
        api_key=source.get("FAVORIOT_API_KEY", "").strip(),
        device_developer_id=source.get("FAVORIOT_DEVICE_DEVELOPER_ID", "").strip(),
        url=source.get("FAVORIOT_URL", DEFAULT_FAVORIOT_URL).strip() or DEFAULT_FAVORIOT_URL,
    )
