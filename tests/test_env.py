import tempfile
import unittest
from pathlib import Path

from plant_monitor.env import load_env_file


class EnvLoaderTest(unittest.TestCase):
    def test_load_env_file_reads_simple_key_values_without_overwriting_existing(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "# local Raspberry Pi settings",
                        "FAVORIOT_API_KEY=key-from-file",
                        "FAVORIOT_DEVICE_DEVELOPER_ID='device-default@user'",
                        "READ_INTERVAL_SECONDS=2",
                    ]
                ),
                encoding="utf-8",
            )
            environ = {"FAVORIOT_API_KEY": "already-exported"}

            load_env_file(env_path, environ=environ)

        self.assertEqual(environ["FAVORIOT_API_KEY"], "already-exported")
        self.assertEqual(environ["FAVORIOT_DEVICE_DEVELOPER_ID"], "device-default@user")
        self.assertEqual(environ["READ_INTERVAL_SECONDS"], "2")

    def test_load_env_file_ignores_missing_file(self):
        environ = {}

        load_env_file(Path("missing.env"), environ=environ)

        self.assertEqual(environ, {})


if __name__ == "__main__":
    unittest.main()
