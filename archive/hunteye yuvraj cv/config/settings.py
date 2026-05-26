from config.loader import load_config


SETTINGS = load_config()

SYSTEM_MODE = SETTINGS["system"]["mode"].upper()
DEBUG_MODE = SETTINGS["system"]["debug"]

CAMERA_NAME = SETTINGS["camera"]["name"]
CAMERA_SLEEP = SETTINGS["camera"]["sleep_seconds"]
WINDOW_NAME = SETTINGS["window"]["name"]

FRAME_WIDTH = SETTINGS["camera"]["width"]
FRAME_HEIGHT = SETTINGS["camera"]["height"]
TARGET_FPS = SETTINGS["camera"]["target_fps"]

AIRSIM_IP = SETTINGS["airsim"]["ip"]

ENABLE_GPU = True

LOG_LEVEL = SETTINGS["logging"]["level"]
