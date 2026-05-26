import time


class FPSCounter:

    def __init__(self):

        self.last_time = time.time()

        self.frames = 0

        self.fps = 0

    def update(self):

        self.frames += 1

        current = time.time()

        delta = current - self.last_time

        if delta >= 1.0:

            self.fps = self.frames / delta

            self.frames = 0

            self.last_time = current

    def get_fps(self):

        return round(self.fps, 2)