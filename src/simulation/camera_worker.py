from config import load_config

from core.worker_base import WorkerBase

from simulation.camera import CameraStream


class CameraWorker(WorkerBase):

    def __init__(self, state, hal=None, config=None):

        self.config = config or load_config()

        super().__init__(
            "CameraWorker",
            loop_interval=self.config["camera"]["sleep_seconds"],
            restartable=True
        )

        self.state = state

        self.camera = CameraStream(hal=hal, config=self.config)

    def safe_run(self):

        while self.running:

            with self.state.profiler.measure("camera_get_frame"):

                frame = self.camera.get_frame()

            if frame is not None:

                self.state.set_latest_frame(frame)

            self.heartbeat()

            self.sleep()
