from datetime import datetime
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from plant_monitor.app import SensorReading
from plant_monitor.debug import build_startup_diagnostics
from plant_monitor.env import load_env_file
from plant_monitor.forecast import (
    FORECAST_RISK_DRY,
    FORECAST_UNKNOWN,
    forecast_soil_moisture,
    load_forecast_model,
)
from plant_monitor.logic import load_favoriot_config
from plant_monitor.notifications import detect_risk_events
from plant_monitor.settings import read_interval_seconds, telegram_config_from_env


BASE_DIR = Path(__file__).resolve().parent
load_env_file(BASE_DIR / ".env")

_truthy = lambda v: str(v).strip().lower() in {"1", "true", "yes", "on"}
_sim_mode = _truthy(os.getenv("SIMULATION_MODE", "false"))
_demo_mode = _truthy(os.getenv("DEMO_MODE", "false"))
if _sim_mode:
    _default_csv = "sim_data.csv"
elif _demo_mode:
    _default_csv = "demo_data.csv"
else:
    _default_csv = "plant_data.csv"
CSV_FILE = Path(os.getenv("CSV_FILE", str(BASE_DIR / _default_csv)))
MODEL_PATH = Path(os.getenv("FORECAST_MODEL_PATH", str(BASE_DIR / "models" / "soil_forecast_sarimax.joblib")))
AUTH_CONFIG_PATH = BASE_DIR / "auth_config.yaml"
FORECAST_MIN_ROWS = int(os.getenv("FORECAST_MIN_ROWS", "4"))
FORECAST_RECENT_AVERAGE_HOURS = float(os.getenv("FORECAST_RECENT_AVERAGE_HOURS", "1"))
FORECAST_DRY_PERCENT = float(os.getenv("FORECAST_DRY_PERCENT", "30"))

NUMERIC_COLUMNS = [
    "temperature",
    "humidity",
    "soil_value",
    "previous_soil_value",
    "moisture_change_rate",
    "vpd",
    "soil_lag_1",
    "soil_lag_2",
    "soil_lag_3",
    "soil_rolling_mean",
    "soil_rate_per_hour",
    "forecast_soil_4hr",
    "forecast_soil_6hr",
    "forecast_soil_8hr",
]


# ── Authentication (custom — no streamlit-authenticator needed) ─────────────

def _load_auth_config() -> dict:
    """Load and validate auth_config.yaml. Shows an error and stops if missing."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        st.error("⚠️ PyYAML not installed. Run: pip install PyYAML bcrypt")
        st.stop()

    if not AUTH_CONFIG_PATH.exists():
        st.error(
            f"⚠️ `auth_config.yaml` not found. "
            "Run `python generate_passwords.py` on the Pi to create users."
        )
        st.stop()

    with open(AUTH_CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        import bcrypt  # noqa: PLC0415
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def require_login() -> tuple[str, str]:
    """
    Show a login form and block access until the user authenticates.
    Auth state is stored in st.session_state for the browser session.
    Returns (name, username) of the logged-in user.
    """
    # Already logged in this session?
    if st.session_state.get("authenticated"):
        return st.session_state["user_name"], st.session_state["username"]

    config = _load_auth_config()
    users = config.get("credentials", {}).get("usernames", {})

    # ── Login form ──────────────────────────────────────────────────────────
    st.markdown("## 🌱 Soil Monitor — Login")
    with st.form("login_form"):
        username_input = st.text_input("Username").strip().lower()
        password_input = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if not submitted:
        st.stop()

    # ── Validate credentials ────────────────────────────────────────────────
    user_info = users.get(username_input)
    if (
        user_info is None
        or not isinstance(user_info, dict)
        or not _verify_password(password_input, user_info.get("password", ""))
    ):
        st.error("❌ Username or password is incorrect")
        st.stop()

    # ── Store session ───────────────────────────────────────────────────────
    st.session_state["authenticated"] = True
    st.session_state["username"] = username_input
    st.session_state["user_name"] = user_info.get("name", username_input)
    st.rerun()


def logout():
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["user_name"] = ""
    st.rerun()




# ── Data loading ────────────────────────────────────────────────────────────

def load_data(csv_path):
    path = Path(csv_path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()

    frame = pd.read_csv(path)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        frame = frame.dropna(subset=["timestamp"]).reset_index(drop=True)
    for column in NUMERIC_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def streamlit_refresh_seconds(env=None):
    source = os.environ if env is None else env
    try:
        value = int(source.get("STREAMLIT_REFRESH_SECONDS", "2"))
    except ValueError:
        return 0
    return max(0, value)


def latest_reading(frame):
    if frame.empty:
        return None

    row = frame.iloc[-1].to_dict()
    timestamp = row.get("timestamp")
    if pd.isna(timestamp):
        timestamp = datetime.now()
    elif hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()

    return SensorReading(
        timestamp=timestamp,
        temperature=None if pd.isna(row.get("temperature")) else row.get("temperature"),
        humidity=None if pd.isna(row.get("humidity")) else row.get("humidity"),
        soil_value=0.0 if pd.isna(row.get("soil_value")) else row.get("soil_value"),
        previous_soil_value=None if pd.isna(row.get("previous_soil_value")) else row.get("previous_soil_value"),
        moisture_change_rate=0.0 if pd.isna(row.get("moisture_change_rate")) else row.get("moisture_change_rate"),
        vpd=None if pd.isna(row.get("vpd")) else row.get("vpd"),
        soil_lag_1=None if pd.isna(row.get("soil_lag_1")) else row.get("soil_lag_1"),
        soil_lag_2=None if pd.isna(row.get("soil_lag_2")) else row.get("soil_lag_2"),
        soil_lag_3=None if pd.isna(row.get("soil_lag_3")) else row.get("soil_lag_3"),
        soil_rolling_mean=None if pd.isna(row.get("soil_rolling_mean")) else row.get("soil_rolling_mean"),
        soil_rate_per_hour=None if pd.isna(row.get("soil_rate_per_hour")) else row.get("soil_rate_per_hour"),
        soil_status=row.get("soil_status", ""),
        pump_status=row.get("pump_status", ""),
        forecast_soil_4hr=None if pd.isna(row.get("forecast_soil_4hr")) else row.get("forecast_soil_4hr"),
        forecast_soil_6hr=None if pd.isna(row.get("forecast_soil_6hr")) else row.get("forecast_soil_6hr"),
        forecast_soil_8hr=None if pd.isna(row.get("forecast_soil_8hr")) else row.get("forecast_soil_8hr"),
        forecast_risk=row.get("forecast_risk", FORECAST_UNKNOWN),
        forecast_recommendation=row.get("forecast_recommendation", "Forecast unavailable."),
        ml_prediction=row.get("ml_prediction", "Unknown"),
        dry_soon_label=row.get("dry_soon_label", ""),
        notification_status=row.get("notification_status", ""),
        debug_status=row.get("debug_status", ""),
    )


def csv_health(frame):
    if frame.empty:
        return "Missing or empty CSV"
    if "timestamp" not in frame.columns or pd.isna(frame.iloc[-1]["timestamp"]):
        return "CSV timestamp missing"

    latest_time = frame.iloc[-1]["timestamp"]
    age_seconds = (pd.Timestamp.now() - latest_time).total_seconds()
    stale_after = max(120, read_interval_seconds() * 3)
    if age_seconds > stale_after:
        if age_seconds < 60:
            return f"CSV stale: latest row is {int(age_seconds)} seconds old"
        return f"CSV stale: latest row is {int(age_seconds // 60)} minutes old"
    return "CSV fresh"


def show_alerts(reading, frame):
    health = csv_health(frame)
    if health != "CSV fresh":
        st.warning(health)
    if not reading:
        return

    events = detect_risk_events(reading)
    if not events and reading.forecast_risk != FORECAST_RISK_DRY and reading.forecast_risk != FORECAST_UNKNOWN:
        st.success("No current risk detected.")
        return

    if reading.forecast_risk == FORECAST_UNKNOWN:
        st.warning("Forecast unavailable. Collect more real sensor rows or train the SARIMAX model.")

    # Determine when it will be dry based on the forecast horizons
    dry_horizon = ""
    if reading.forecast_soil_4hr is not None and reading.forecast_soil_4hr < FORECAST_DRY_PERCENT:
        dry_horizon = " in 4 hours"
    elif reading.forecast_soil_6hr is not None and reading.forecast_soil_6hr < FORECAST_DRY_PERCENT:
        dry_horizon = " in 6 hours"
    elif reading.forecast_soil_8hr is not None and reading.forecast_soil_8hr < FORECAST_DRY_PERCENT:
        dry_horizon = " in 8 hours"

    for event in events:
        if event in {"DRY", "Dry Soon", "Forecast Dry"}:
            continue  # handled in the combined alert below
        elif event == "WET":
            st.warning("Alert: WET / overwatering risk")
        else:
            st.warning(f"Alert: {event}")

    # Display a single, combined dry alert if needed
    if "DRY" in events:
        st.error("🚨 Alert: Soil is currently DRY!")
    elif reading.forecast_risk == FORECAST_RISK_DRY or "Forecast Dry" in events or "Dry Soon" in events:
        st.error(f"⚠️ Forecast Alert: Soil moisture is predicted to fall below the dry threshold{dry_horizon}.")


@st.cache_resource(show_spinner=False)
def load_forecast_bundle():
    return load_forecast_model(MODEL_PATH)


def forecast_from_history(frame):
    bundle = load_forecast_bundle()
    if not bundle.is_ready:
        return None
    if frame.empty:
        return None
    return forecast_soil_moisture(
        bundle,
        frame,
        horizons_hours=[4, 6, 8],
        recent_average_hours=FORECAST_RECENT_AVERAGE_HOURS,
        dry_threshold=FORECAST_DRY_PERCENT,
        control_mode=os.getenv("ML_CONTROL_MODE", "recommend"),
    )


def chart_sections(frame):
    available_sections = [
        ("Soil Moisture Trend", ["soil_value"]),
        ("Temperature Trend", ["temperature"]),
        ("Humidity Trend", ["humidity"]),
        ("Moisture Change Rate", ["moisture_change_rate"]),
        ("Forecast Soil Moisture", ["soil_value", "forecast_soil_4hr", "forecast_soil_6hr", "forecast_soil_8hr"]),
    ]
    return [
        (title, columns)
        for title, columns in available_sections
        if all(column in frame.columns for column in columns)
    ]


def show_charts(frame, chart_placeholder):
    """
    Render all trend charts inside `chart_placeholder`.
    Using a single placeholder prevents the entire chart section from
    disappearing and reappearing on every fragment rerun (no more flash).
    """
    with chart_placeholder.container():
        if frame.empty or "timestamp" not in frame.columns:
            st.info("No chart data available yet.")
            return

        import plotly.graph_objects as go

        chart_frame = frame.dropna(subset=["timestamp"]).set_index("timestamp")
        for title, columns in chart_sections(chart_frame):
            st.subheader(title)
            existing_columns = [c for c in columns if c in chart_frame.columns]
            if not existing_columns:
                continue
            fig = go.Figure()
            for col in existing_columns:
                fig.add_trace(go.Scatter(
                    x=chart_frame.index,
                    y=chart_frame[col],
                    mode="lines",
                    name=col,
                ))
            fig.update_layout(
                title=title,
                xaxis_title="Time",
                yaxis_title="Value",
                height=300,
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)


def format_forecast_value(value):
    if value is None or pd.isna(value):
        return "N/A"
    val = float(value)
    state = "DRY" if val < FORECAST_DRY_PERCENT else "OPTIMAL"
    return f"{val:.1f}% ({state})"


def show_forecast_chart(reading, forecast_result, forecast_placeholder):
    """
    Render the forecast chart inside `forecast_placeholder` to avoid flash.
    """
    with forecast_placeholder.container():
        if not reading:
            return
        if forecast_result is None:
            st.info("Forecast chart will appear after the SARIMAX model is trained and enough rows are available.")
            return

        import plotly.graph_objects as go

        chart_frame = pd.DataFrame(
            {
                "Soil Moisture": [
                    reading.soil_value,
                    forecast_result.forecast_soil_4hr,
                    forecast_result.forecast_soil_6hr,
                    forecast_result.forecast_soil_8hr,
                ],
                "Dry Threshold": [FORECAST_DRY_PERCENT] * 4,
            },
            index=["Now", "4h", "6h", "8h"],
        )

        time_labels = list(chart_frame.index)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time_labels,
            y=chart_frame["Soil Moisture"],
            mode="lines+markers",
            name="Soil Moisture",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=8),
        ))
        fig.add_trace(go.Scatter(
            x=time_labels,
            y=chart_frame["Dry Threshold"],
            mode="lines",
            name="Dry Threshold",
            line=dict(color="#ff7f0e", width=2, dash="dash"),
        ))
        fig.update_layout(
            title="Current and Forecast Soil Moisture",
            xaxis_title="Time",
            yaxis_title="Soil Moisture (%)",
            height=400,
            hovermode="x unified",
        )
        st.plotly_chart(fig)


def show_debug(frame):
    favoriot_config = load_favoriot_config()
    telegram_config = telegram_config_from_env()
    diagnostics = build_startup_diagnostics(
        dht_pin="from .env",
        soil_channel="from .env",
        relay_pin="from .env",
        csv_path=CSV_FILE,
        favoriot_config=favoriot_config,
        telegram_config=telegram_config,
        model_path=MODEL_PATH,
        simulation_mode=False,
    )

    st.subheader("Configuration Status")
    st.json(diagnostics)
    st.write("CSV path:", str(CSV_FILE))
    st.write("Rows loaded:", len(frame))
    st.write("Favoriot configured:", favoriot_config.is_configured)
    st.write("Telegram configured:", telegram_config.is_configured)
    st.write("Forecast model file exists:", MODEL_PATH.exists())
    st.write("Rows available for forecasting:", len(frame))
    st.write("Forecast minimum rows:", FORECAST_MIN_ROWS)
    if not MODEL_PATH.exists():
        forecast_readiness = "FORECAST_MODEL_MISSING"
    elif len(frame) < FORECAST_MIN_ROWS:
        forecast_readiness = "FORECAST_NOT_ENOUGH_DATA"
    else:
        forecast_readiness = "OK"
    st.write("Forecast readiness:", forecast_readiness)
    st.write("Recent average window (hours):", FORECAST_RECENT_AVERAGE_HOURS)
    if not frame.empty:
        latest = frame.iloc[-1]
        st.write("Latest VPD:", str(latest.get("vpd", "N/A")))
        st.json({
            "Latest forecasts": {
                "4h": str(latest.get("forecast_soil_4hr", "N/A")),
                "6h": str(latest.get("forecast_soil_6hr", "N/A")),
                "8h": str(latest.get("forecast_soil_8hr", "N/A")),
            }
        })

    st.subheader("Latest CSV Row")
    if frame.empty:
        st.info("No data rows yet.")
    else:
        st.json(frame.iloc[-1].astype(str).to_dict())

    st.subheader("Common Wiring Hints")
    st.markdown(
        """
        - DHT11 data pin should match `DHT_PIN` such as `D4` or `D17`.
        - MCP3008 CH0 should match `SOIL_CHANNEL=0` unless the AO wire is moved.
        - Relay is active LOW: `GPIO.LOW` means pump ON, `GPIO.HIGH` means pump OFF.
        - Enable I2C for OLED and SPI for MCP3008 using `sudo raspi-config`.
        - Use `SIMULATION_MODE=true` and `RUN_ONCE=true` to test without hardware.
        """
    )


def render_dashboard(refresh_seconds, username):
    frame = load_data(CSV_FILE)
    reading = latest_reading(frame)
    forecast_result = forecast_from_history(frame)

    if forecast_result is not None and reading is not None:
        reading = SensorReading(
            timestamp=reading.timestamp,
            temperature=reading.temperature,
            humidity=reading.humidity,
            soil_value=reading.soil_value,
            previous_soil_value=reading.previous_soil_value,
            moisture_change_rate=reading.moisture_change_rate,
            vpd=reading.vpd,
            soil_lag_1=reading.soil_lag_1,
            soil_lag_2=reading.soil_lag_2,
            soil_lag_3=reading.soil_lag_3,
            soil_rolling_mean=reading.soil_rolling_mean,
            soil_rate_per_hour=reading.soil_rate_per_hour,
            soil_status=reading.soil_status,
            pump_status=reading.pump_status,
            forecast_soil_4hr=forecast_result.forecast_soil_4hr,
            forecast_soil_6hr=forecast_result.forecast_soil_6hr,
            forecast_soil_8hr=forecast_result.forecast_soil_8hr,
            forecast_risk=forecast_result.forecast_risk,
            forecast_recommendation=forecast_result.forecast_recommendation,
            ml_prediction=forecast_result.ml_prediction,
            dry_soon_label=reading.dry_soon_label,
            notification_status=reading.notification_status,
            debug_status=reading.debug_status,
        )

    alerts_placeholder = st.empty()
    metrics_placeholder = st.empty()

    dashboard_tab, data_tab, debug_tab = st.tabs(["Dashboard", "Recent Data", "Debug"])

    # ── Pre-create stable placeholders so charts update IN-PLACE (no flash) ──
    # These placeholders are created once outside the fragment cycle.
    with dashboard_tab:
        forecast_placeholder = st.empty()
        charts_placeholder = st.empty()
    with data_tab:
        data_placeholder = st.empty()
    with debug_tab:
        debug_placeholder = st.empty()

    def draw_content():
        fresh_frame = load_data(CSV_FILE)
        fresh_reading = latest_reading(fresh_frame)
        fresh_forecast = forecast_from_history(fresh_frame)

        with alerts_placeholder.container():
            show_alerts(fresh_reading, fresh_frame)

        with metrics_placeholder.container():
            if fresh_reading:
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("Soil Moisture", f"{fresh_reading.soil_value:.1f}% ({fresh_reading.soil_status})")
                col2.metric("Forecast 4h", format_forecast_value(fresh_reading.forecast_soil_4hr))
                col3.metric("Forecast 6h", format_forecast_value(fresh_reading.forecast_soil_6hr))
                col4.metric("Forecast 8h", format_forecast_value(fresh_reading.forecast_soil_8hr))
                col5.metric("Pump", fresh_reading.pump_status)

                accuracy_path = MODEL_PATH.parent / "model_accuracy.json"
                if accuracy_path.exists():
                    try:
                        import json
                        with open(accuracy_path, "r") as f:
                            acc = json.load(f)
                            st.caption(f"**Model Accuracy (Test Data)**: MAE ±{acc['mae']}%  |  RMSE {acc['rmse']}%")
                    except Exception:
                        pass

        show_forecast_chart(fresh_reading, fresh_forecast, forecast_placeholder)
        show_charts(fresh_frame, charts_placeholder)

        with data_placeholder.container():
            if fresh_frame.empty:
                st.info("No CSV readings found yet.")
            else:
                st.markdown(fresh_frame.tail(50).to_html(index=False), unsafe_allow_html=True)

        with debug_placeholder.container():
            show_debug(fresh_frame)

    if refresh_seconds > 0:
        @st.fragment(run_every=refresh_seconds)
        def live_content():
            draw_content()
        live_content()
    else:
        draw_content()


def main():
    st.set_page_config(page_title="Smart Plant Dashboard", page_icon=":seedling:", layout="wide")
    refresh_seconds = streamlit_refresh_seconds()

    # ── Sidebar: show login status ─────────────────────────────────────────
    st.sidebar.title("🌱 Soil Monitor")

    # Require login before showing anything
    name, username = require_login()

    st.sidebar.success(f"Logged in as **{name}**")
    st.sidebar.caption(f"Username: `{username}`")
    if st.sidebar.button("Logout"):
        logout()
    st.sidebar.divider()
    pause_updates = st.sidebar.checkbox("⏸️ Pause Live Updates", value=False, help="Check this to temporarily stop the dashboard from redrawing so you can zoom and interact with the charts.")
    if pause_updates:
        refresh_seconds = 0

    st.sidebar.caption(
        f"Live updates: {'off' if refresh_seconds <= 0 else str(refresh_seconds) + 's'}"
    )

    st.title("Smart Plant Monitoring Dashboard")
    st.caption(
        "Predictive irrigation dashboard for soil dryness risk, notifications, and debugging. "
        f"Live updates: {'off' if refresh_seconds <= 0 else str(refresh_seconds) + 's fragment reruns'}. "
        f"Forecast source: {'live SARIMAX model' if load_forecast_bundle().is_ready else 'CSV fallback only'}."
    )

    render_dashboard(refresh_seconds, username)


if __name__ == "__main__":
    main()
