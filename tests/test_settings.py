import unittest

from plant_monitor.settings import (
    DEFAULT_READ_INTERVAL_SECONDS,
    debug_mode_enabled,
    ml_control_mode,
    read_interval_seconds,
    run_once_enabled,
    simulation_mode_enabled,
    telegram_config_from_env,
)


class SettingsTest(unittest.TestCase):
    def test_default_sampling_interval_is_ten_minutes(self):
        self.assertEqual(DEFAULT_READ_INTERVAL_SECONDS, 600)
        self.assertEqual(read_interval_seconds({}), 600.0)

    def test_read_interval_seconds_can_be_overridden_from_environment(self):
        self.assertEqual(read_interval_seconds({"READ_INTERVAL_SECONDS": "30"}), 30.0)

    def test_runtime_flags_are_read_from_environment(self):
        env = {
            "DEBUG_MODE": "true",
            "SIMULATION_MODE": "1",
            "RUN_ONCE": "yes",
            "ML_CONTROL_MODE": "control",
        }

        self.assertTrue(debug_mode_enabled(env))
        self.assertTrue(simulation_mode_enabled(env))
        self.assertTrue(run_once_enabled(env))
        self.assertEqual(ml_control_mode(env), "control")

    def test_ml_control_mode_defaults_to_recommend_when_invalid(self):
        self.assertEqual(ml_control_mode({"ML_CONTROL_MODE": "danger"}), "recommend")

    def test_telegram_config_from_env(self):
        config = telegram_config_from_env(
            {
                "TELEGRAM_ENABLED": "true",
                "TELEGRAM_BOT_TOKEN": "token",
                "TELEGRAM_CHAT_ID": "chat",
                "NOTIFICATION_COOLDOWN_SECONDS": "900",
            }
        )

        self.assertTrue(config.enabled)
        self.assertTrue(config.is_configured)
        self.assertEqual(config.cooldown_seconds, 900)


if __name__ == "__main__":
    unittest.main()
