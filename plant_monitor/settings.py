import os


DEFAULT_READ_INTERVAL_SECONDS = 600


def read_interval_seconds(env=None):
    source = os.environ if env is None else env
    return float(source.get("READ_INTERVAL_SECONDS", DEFAULT_READ_INTERVAL_SECONDS))
