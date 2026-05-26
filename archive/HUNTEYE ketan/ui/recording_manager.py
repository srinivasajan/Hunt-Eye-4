import os
import time
import threading
import numpy as np


class RecordingManager:
    def __init__(self):
        self._frames = []
        self._telemetry = []
        self._recording = False
        self._lock = threading.Lock()
        self._save_path = None

    def start(self, save_path):
        with self._lock:
            self._frames = []
            self._telemetry = []
            self._recording = True
            self._save_path = save_path
            folder = os.path.dirname(save_path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            else:
                os.makedirs("recordings", exist_ok=True)

    def add_frame(self, frame, telemetry=None):
        if not self._recording:
            return
        with self._lock:
            self._frames.append(frame.copy())
            self._telemetry.append({
                "timestamp": time.time(),
                **(telemetry or {})
            })

    def stop(self):
        with self._lock:
            self._recording = False
            if not self._frames:
                return ""
            save_path = self._save_path or "recordings/rec_unnamed"
            try:
                np.save(f"{save_path}_frames.npy", np.array(self._frames))
                print(f"[RecordingManager] Saved {len(self._frames)} frames")
            except Exception as e:
                print(f"[RecordingManager] Save error: {e}")
            self._frames = []
            self._telemetry = []
            return save_path

    def load(self, save_path):
        try:
            frames = list(np.load(f"{save_path}_frames.npy", allow_pickle=True))
            print(f"[RecordingManager] Loaded {len(frames)} frames")
            return frames
        except Exception as e:
            print(f"[RecordingManager] Load error: {e}")
            return []

    @property
    def is_recording(self):
        return self._recording

    @property
    def frame_count(self):
        with self._lock:
            return len(self._frames)