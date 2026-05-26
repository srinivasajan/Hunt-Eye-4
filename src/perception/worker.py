import cv2
import numpy as np
import time
import torch
from core.worker_base import WorkerBase
from core.logger import Logger

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

# Throttle interval in seconds for repeated per-frame error messages
_ERR_THROTTLE_S = 30.0


class PerceptionWorker(WorkerBase):
    def __init__(self, state, config):
        super().__init__(name="perception", loop_interval=0.03)
        self.state = state
        self.config = config
        self.model = None
        self.midas = None
        self.midas_transform = None
        self._last_yolo_err_t: float = 0.0
        self._last_midas_err_t: float = 0.0

        if YOLO is not None:
            try:
                import sys
                from pathlib import Path
                
                model_name = self.config.get("perception", {}).get("model", "yolov8n.pt")
                
                if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    model_path = Path(sys._MEIPASS) / model_name
                else:
                    model_path = Path(model_name).resolve()
                    
                self.model = YOLO(str(model_path))
            except Exception as e:
                Logger.error(f"Failed to load YOLO model: {e}")
        else:
            Logger.warning("ultralytics not installed — YOLO detection disabled")
        
        try:
            # MiDaS depth estimation
            # Note: MiDaS_small requires the 'timm' package.
            # If timm is missing, depth estimation is silently disabled.
            model_type = "MiDaS_small"
            self.midas = torch.hub.load("intel-isl/MiDaS", model_type)
            self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
            self.midas.to(self.device)
            self.midas.eval()
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            self.midas_transform = midas_transforms.small_transform
        except ImportError as e:
            # Most commonly: 'timm' is not installed
            Logger.warning(
                f"MiDaS depth estimation disabled — missing dependency: {e}. "
                "Install 'timm' to enable depth overlays."
            )
        except Exception as e:
            Logger.error(f"Failed to load MiDaS model: {e}")

    def safe_run(self):
        while self.running:
            self.heartbeat()

            if self.model is None and self.midas is None:
                self.sleep(1.0)
                continue

            frame = self.state.get_latest_frame()
            if frame is None:
                self.sleep()
                continue
            
            # --- YOLO/ByteTrack Tracking ---
            target_bbox = None
            if self.model is not None:
                try:
                    # YOLOv8 built-in ByteTrack
                    results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
                    
                    current_time = time.time()
                    with self.state.lock:
                        active_id = self.state.active_target_id
                        target_last_seen = getattr(self.state, 'target_last_seen', 0.0)
                        
                    found_target = False
                    best_conf = 0.0
                    best_id = -1
                    best_bbox = None
                    detections_list = []
                    tracks_list = []

                    conf_threshold = self.config.get("perception", {}).get("confidence_threshold", 0.50)
                    
                    if len(results) > 0 and results[0].boxes is not None:
                        for box in results[0].boxes:
                            if box.id is None:
                                continue
                            conf = float(box.conf[0])
                            if conf < conf_threshold:
                                continue
                                
                            track_id = int(box.id[0])
                            bbox_coords = box.xyxy[0].tolist()

                            det = {
                                "bbox": bbox_coords,
                                "confidence": round(conf, 2),
                                "label": "target",
                                "track_id": track_id
                            }
                            detections_list.append(det)
                            tracks_list.append({
                                "track_id": track_id,
                                "bbox": bbox_coords,
                                "tlwh": bbox_coords,
                                "score": conf
                            })

                            if active_id != -1 and track_id == active_id:
                                target_bbox = bbox_coords
                                found_target = True
                            
                            if active_id == -1 and conf > best_conf:
                                best_conf = conf
                                best_id = track_id
                                best_bbox = bbox_coords

                    with self.state.lock:
                        # Write HUD elements
                        self.state.detections = detections_list
                        self.state.tracks = tracks_list
                        
                        if found_target:
                            self.state.active_target_id = active_id
                            self.state.target_last_seen = current_time
                            self.state.target_bbox = target_bbox
                        elif not found_target and best_id != -1:
                            # Lock onto the new most-confident target
                            self.state.active_target_id = best_id
                            self.state.target_last_seen = current_time
                            self.state.target_bbox = best_bbox
                        elif not found_target and active_id != -1:
                            # Target occluded. 2.0 seconds occlusion tracking timeout.
                            if current_time - target_last_seen > 2.0:
                                self.state.active_target_id = -1
                                self.state.target_bbox = None
                            else:
                                # Maintain ID but drop bbox so drone hovers until reappearance
                                self.state.target_bbox = None
                                
                                # Send faded track to HUD during occlusion
                                # We don't have the last exact bbox from YOLO, but we can maintain ID
                except Exception as e:
                    now = time.time()
                    if now - self._last_yolo_err_t >= _ERR_THROTTLE_S:
                        Logger.error(f"YOLO Tracking error: {e}")
                        self._last_yolo_err_t = now

            # --- MiDaS Depth ---
            depth_map = None
            if self.midas is not None and self.midas_transform is not None:
                try:
                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    input_batch = self.midas_transform(img).to(self.device)
                    with torch.no_grad():
                        prediction = self.midas(input_batch)
                        prediction = torch.nn.functional.interpolate(
                            prediction.unsqueeze(1),
                            size=img.shape[:2],
                            mode="bicubic",
                            align_corners=False,
                        ).squeeze()
                    depth_map = prediction.cpu().numpy()
                    
                    # Compute an obstacle cost map from depth
                    # Normalize depth to 0-100 range for planner/cost_map
                    depth_min = depth_map.min()
                    depth_max = depth_map.max()
                    if depth_max > depth_min:
                        cost_map_float = (depth_map - depth_min) / (depth_max - depth_min) * 100.0
                        # Downsample obstacle map for planner (e.g., 20x20)
                        cost_map_small = cv2.resize(cost_map_float, (20, 20), interpolation=cv2.INTER_AREA)
                        
                        with self.state.lock:
                            self.state.cost_map = cost_map_small
                            self.state.depth_frame = depth_map
                except Exception as e:
                    now = time.time()
                    if now - self._last_midas_err_t >= _ERR_THROTTLE_S:
                        Logger.error(f"MiDaS Depth error: {e}")
                        self._last_midas_err_t = now
            
            with self.state.lock:
                if target_bbox is not None:
                    self.state.target_bbox = target_bbox

            self.sleep()

