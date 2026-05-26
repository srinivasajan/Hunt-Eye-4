import logging
import os

from config.loader import load_config
from core.paths import get_app_dir


CONFIG = load_config()

LOG_FOLDER = get_app_dir() / CONFIG["logging"]["folder"]
LOG_LEVEL = getattr(logging, CONFIG["logging"]["level"].upper(), logging.INFO)

LOG_FOLDER.mkdir(parents=True, exist_ok=True)


# Separate handlers: File gets everything (DEBUG/INFO), Console gets WARNING+ unless debug mode is strictly on
file_handler = logging.FileHandler(str(LOG_FOLDER / "hunt_eye.log"))
file_handler.setLevel(LOG_LEVEL)

stream_handler = logging.StreamHandler()
# Operator mode is quieter on the console
console_level = logging.DEBUG if CONFIG["system"].get("debug") else logging.WARNING
stream_handler.setLevel(console_level)

logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(levelname)s] %(asctime)s | %(message)s",
    handlers=[file_handler, stream_handler]
)

class Logger:

    @staticmethod
    def info(message):
        logging.info(message)

    @staticmethod
    def error(message):
        logging.error(message)

    @staticmethod
    def warning(message):
        logging.warning(message)
