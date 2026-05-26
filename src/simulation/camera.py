from config import load_config
from core.hal import HAL


class CameraStream:

    def __init__(self, hal=None, config=None):

        self.config = config or load_config()

        self.hal = hal or HAL(self.config)

    def get_frame(self):

        return self.hal.get_frame()
