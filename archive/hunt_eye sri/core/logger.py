import logging
import os

from config.loader import load_config


CONFIG = load_config()

LOG_FOLDER = CONFIG["logging"]["folder"]
LOG_LEVEL = getattr(logging, CONFIG["logging"]["level"].upper(), logging.INFO)

os.makedirs(LOG_FOLDER, exist_ok=True)


logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(levelname)s] %(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_FOLDER}/hunt_eye.log"),
        logging.StreamHandler()
    ]
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
