"""
Base class for detection workers in the HuntEye perception pipeline.

Defines the standard interface for workers that process camera frames
and produce object detections to be consumed by tracking workers.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from core.worker_base import WorkerBase
from core.logger import Logger


class DetectorWorkerBase(WorkerBase):
    """
    Base class for detection workers (e.g., YOLO, MiDaS, segmentation models).
    
    Expected SharedState contract:
    - Reads: latest_frame (np.ndarray)
    - Writes: detections (List[Dict])
    
    Detection format:
    {
        "bbox": [x1, y1, x2, y2],  # Absolute pixel coordinates
        "confidence": float,        # Detection confidence [0.0, 1.0]
        "class_id": int,            # Optional class identifier
        "class_name": str,          # Optional class name
        # Additional fields can be added as needed
    }
    
    All coordinates should be in the same frame space as latest_frame.
    """
    
    def __init__(self, 
                 name: str, 
                 state: Any, 
                 loop_interval: float = 0.0,
                 restartable: bool = True,
                 # Detector-specific configuration can be added here
                 ):
        """
        Initialize the detector worker base.
        
        Args:
            name: Worker name (for logging and identification)
            state: SharedState instance for inter-worker communication
            loop_interval: Time to sleep between processing cycles (seconds)
            restartable: Whether this worker can be auto-restarted by watchdog
        """
        super().__init__(name=name, loop_interval=loop_interval, restartable=restartable)
        self.state = state
        self.logger = Logger
        
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess the input frame before detection.
        Override this method for detector-specific preprocessing.
        
        Args:
            frame: Input frame as numpy array (H, W, C) in BGR format
            
        Returns:
            Preprocessed frame ready for inference
        """
        # Default: return frame as-is
        return frame
        
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Perform object detection on a single frame.
        This method MUST be implemented by subclasses.
        
        Args:
            frame: Preprocessed frame as numpy array
            
        Returns:
            List of detection dictionaries following the format specified
            in the class docstring
        """
        raise NotImplementedError("Subclasses must implement detect() method")
        
    def postprocess_detections(self, 
                              raw_detections: List[Dict[str, Any]], 
                              frame_shape: Tuple[int, int, int]) -> List[Dict[str, Any]]:
        """
        Postprocess raw detection outputs.
        Override this method for detector-specific postprocessing (e.g., NMS, filtering).
        
        Args:
            raw_detections: Raw detection outputs from detect() method
            frame_shape: Shape of the original frame (height, width, channels)
            
        Returns:
            Filtered and processed detection dictionaries
        """
        # Default: return detections as-is
        return raw_detections
        
    def safe_run(self) -> None:
        """
        Main detection loop. Reads frames, runs detection, writes results.
        """
        while self.running:
            start_time = self.state.profiler.measure(f"{self.name}_cycle") \
                        if hasattr(self.state, 'profiler') else None
            
            try:
                # Get latest frame from shared state
                frame = self.state.get_latest_frame()
                
                if frame is None:
                    # No frame available yet, sleep briefly
                    self.sleep(0.01)
                    continue
                    
                # Preprocess frame
                processed_frame = self.preprocess_frame(frame)
                
                # Run detection
                raw_detections = self.detect(processed_frame)
                
                # Postprocess detections
                detections = self.postprocess_detections(
                    raw_detections, 
                    frame.shape
                )
                
                # Write detections to shared state
                with self.state.lock:
                    self.state.detections = detections
                    
                # Update heartbeat
                self.heartbeat()
                
                # Measure cycle latency if profiler available
                if start_time is not None:
                    with start_time:
                        pass  # Context manager handles timing
                        
            except Exception as e:
                self.logger.error(f"Detection error in {self.name}: {e}")
                self.failed = True
                self.error = str(e)
                # Continue running to allow recovery attempt
                self.sleep(1.0)
                
            # Sleep for loop interval (if any)
            self.sleep()