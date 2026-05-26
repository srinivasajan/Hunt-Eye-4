"""
Replay System for HuntEye Dashboard (Dev 1.2).

Provides functionality to replay recorded sessions from video files
and associated telemetry/session data.
"""

import os
import cv2
import json
import time
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from ui.ops_state import EventLog, TelemetryHistory, MissionState, OperatorControls, SessionExporter
from core.logger import Logger


class SessionReplay:
    """
    System for replaying recorded HuntEye sessions.
    
    Can playback:
    - Video recordings (MP4 files)
    - Telemetry history
    - Event logs
    - Mission data
    - Operator control history
    """
    
    def __init__(self, 
                 recordings_folder: str = "recordings",
                 sessions_folder: str = "sessions"):
        """
        Initialize the replay system.
        
        Args:
            recordings_folder: Folder containing video recordings
            sessions_folder: Folder containing session export files (JSON)
        """
        self.recordings_folder = Path(recordings_folder)
        self.sessions_folder = Path(sessions_folder)
        
        # Ensure folders exist
        self.recordings_folder.mkdir(exist_ok=True)
        self.sessions_folder.mkdir(exist_ok=True)
        
        # Playback state
        self.is_playing = False
        self.is_paused = False
        self.current_frame_index = 0
        self.total_frames = 0
        self.fps = 30.0
        self.start_time = 0.0
        self.pause_time = 0.0
        
        # Data stores
        self.video_capture = None
        self.telemetry_history: List[Dict] = []
        self.event_log: List[Dict] = []
        self.mission_data: Dict = {}
        self.operator_history: List[Dict] = []
        self.frame_timestamps: List[float] = []
        
        # UI components (will be set by main application)
        self.dashboard = None
        self.event_log_ui = None
        self.telemetry_history_ui = None
        self.mission_state_ui = None
        self.operator_controls_ui = None
        self.session_exporter_ui = None
        
    def set_ui_components(self, 
                         dashboard=None,
                         event_log_ui=None,
                         telemetry_history_ui=None,
                         mission_state_ui=None,
                         operator_controls_ui=None,
                         session_exporter_ui=None):
        """Set UI components for updating during replay."""
        self.dashboard = dashboard
        self.event_log_ui = event_log_ui
        self.telemetry_history_ui = telemetry_history_ui
        self.mission_state_ui = mission_state_ui
        self.operator_controls_ui = operator_controls_ui
        self.session_exporter_ui = session_exporter_ui
    
    def list_available_sessions(self) -> List[Dict[str, str]]:
        """
        List all available recording sessions.
        
        Returns:
            List of dictionaries with session info:
            {
                'name': session name (without extension),
                'video': path to video file,
                'session': path to session JSON file,
                'timestamp': session timestamp
            }
        """
        sessions = []
        
        # Look for video files
        video_extensions = ['.mp4', '.avi', '.mov']
        video_files = []
        for ext in video_extensions:
            video_files.extend(self.recordings_folder.glob(f"*{ext}"))
        
        for video_file in video_files:
            # Look for corresponding session file
            session_file = self.sessions_folder / f"{video_file.stem}_snapshot.json"
            if not session_file.exists():
                # Try alternative naming
                session_file = self.sessions_folder / f"snapshot_{video_file.stem}.json"
            
            session_info = {
                'name': video_file.stem,
                'video': str(video_file),
                'session': str(session_file) if session_file.exists() else None,
                'timestamp': video_file.stat().st_mtime
            }
            sessions.append(session_info)
        
        # Sort by timestamp (newest first)
        sessions.sort(key=lambda x: x['timestamp'], reverse=True)
        return sessions
    
    def load_session(self, video_path: str, session_path: Optional[str] = None) -> bool:
        """
        Load a session for replay.
        
        Args:
            video_path: Path to video recording file
            session_path: Path to session JSON file (optional, will try to find automatically)
            
        Returns:
            True if session loaded successfully
        """
        try:
            # Stop any current playback
            self.stop()
            
            # Load video
            self.video_capture = cv2.VideoCapture(video_path)
            if not self.video_capture.isOpened():
                Logger.error(f"Failed to open video file: {video_path}")
                return False
            
            self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            if self.fps <= 0:
                self.fps = 30.0  # Default fallback
            
            Logger.info(f"Loaded video: {video_path} | frames: {self.total_frames} | FPS: {self.fps}")
            
            # Load session data if provided or found
            if session_path is None:
                # Try to find session file automatically
                video_path_obj = Path(video_path)
                session_path = str(self.sessions_folder / f"{video_path_obj.stem}_snapshot.json")
                if not Path(session_path).exists():
                    session_path = str(self.sessions_folder / f"snapshot_{video_path_obj.stem}.json")
            
            if session_path and Path(session_path).exists():
                self._load_session_data(session_path)
            else:
                Logger.warning(f"No session data found for: {video_path}")
                # Initialize empty data structures
                self.telemetry_history = []
                self.event_log = []
                self.mission_data = {}
                self.operator_history = []
                self.frame_timestamps = []
            
            # Reset playback state
            self.current_frame_index = 0
            self.is_playing = False
            self.is_paused = False
            
            return True
            
        except Exception as e:
            Logger.error(f"Failed to load session: {e}")
            self.stop()
            return False
    
    def _load_session_data(self, session_path: str):
        """Load session data from JSON file."""
        try:
            with open(session_path, 'r') as f:
                session_data = json.load(f)
            
            # Extract data arrays
            self.telemetry_history = session_data.get('telemetry_history', [])
            self.event_log = session_data.get('event_log', [])
            self.mission_data = session_data.get('mission', {})
            self.operator_history = session_data.get('operator_history', [])
            self.frame_timestamps = session_data.get('frame_timestamps', [])
            
            # If no frame timestamps, generate them based on FPS and frame count
            if not self.frame_timestamps and self.total_frames > 0:
                self.frame_timestamps = [
                    i / self.fps for i in range(self.total_frames)
                ]
            
            Logger.info(f"Loaded session data: {len(self.telemetry_history)} telemetry samples, "
                       f"{len(self.event_log)} events")
                       
        except Exception as e:
            Logger.error(f"Failed to load session data from {session_path}: {e}")
            # Initialize empty data structures
            self.telemetry_history = []
            self.event_log = []
            self.mission_data = {}
            self.operator_history = []
            self.frame_timestamps = []
    
    def play(self):
        """Start or resume playback."""
        if not self.video_capture or not self.video_capture.isOpened():
            Logger.warning("No video loaded for playback")
            return False
        
        if self.is_paused:
            # Resume from pause
            self.is_paused = False
            # Adjust start time to account for pause duration
            pause_duration = time.time() - self.pause_time
            self.start_time += pause_duration
            Logger.info("Replay resumed")
        else:
            # Start from beginning or current position
            self.start_time = time.time() - (self.current_frame_index / self.fps)
            self.is_playing = True
            Logger.info(f"Replay started from frame {self.current_frame_index}")
        
        return True
    
    def pause(self):
        """Pause playback."""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.pause_time = time.time()
            Logger.info("Replay paused")
            return True
        return False
    
    def stop(self):
        """Stop playback and reset to beginning."""
        self.is_playing = False
        self.is_paused = False
        
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
        
        self.current_frame_index = 0
        Logger.info("Replay stopped")
    
    def seek_to_frame(self, frame_index: int) -> bool:
        """
        Seek to a specific frame index.
        
        Args:
            frame_index: Frame index to seek to (0-based)
            
        Returns:
            True if seek was successful
        """
        if not self.video_capture or not self.video_capture.isOpened():
            return False
        
        if frame_index < 0 or frame_index >= self.total_frames:
            Logger.warning(f"Invalid frame index: {frame_index} (valid: 0-{self.total_frames-1})")
            return False
        
        self.current_frame_index = frame_index
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        
        # Update time-based seeking
        if self.frame_timestamps and frame_index < len(self.frame_timestamps):
            target_time = self.frame_timestamps[frame_index]
            self.start_time = time.time() - target_time
        
        Logger.debug(f"Seeked to frame: {frame_index}")
        return True
    
    def seek_to_time(self, seconds: float) -> bool:
        """
        Seek to a specific time in seconds.
        
        Args:
            seconds: Time in seconds from start
            
        Returns:
            True if seek was successful
        """
        if self.total_frames == 0 or self.fps <= 0:
            return False
        
        frame_index = int(seconds * self.fps)
        return self.seek_to_frame(frame_index)
    
    def get_current_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Get the current frame for playback.
        
        Returns:
            Tuple of (success, frame) where frame is None if failed
        """
        if not self.is_playing or self.is_paused:
            # If paused or not playing, return last frame without advancing
            if self.current_frame_index > 0:
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_index - 1)
                ret, frame = self.video_capture.read()
                if ret:
                    return True, frame
            return False, None
        
        # Calculate expected frame based on time
        elapsed_time = time.time() - self.start_time
        expected_frame = int(elapsed_time * self.fps)
        
        # Check if we've reached the end
        if expected_frame >= self.total_frames:
            self.stop()
            return False, None
        
        # If we're significantly behind, skip frames to catch up
        if expected_frame > self.current_frame_index + 1:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, expected_frame)
            self.current_frame_index = expected_frame
        
        # Read the frame
        ret, frame = self.video_capture.read()
        if ret:
            self.current_frame_index += 1
            return True, frame
        else:
            # End of video or read error
            self.stop()
            return False, None
    
    def get_session_data_at_time(self, time_seconds: float) -> Dict[str, Any]:
        """
        Get session data (telemetry, events, etc.) at a specific time.
        
        Args:
            time_seconds: Time in seconds from start of session
            
        Returns:
            Dictionary containing data at that time
        """
        result = {
            'telemetry': {},
            'events': [],
            'mission': self.mission_data.copy(),
            'operator': {},
            'frame_index': 0
        }
        
        # Find telemetry at or before this time
        if self.telemetry_history:
            # Binary search would be more efficient, but linear is OK for moderate sizes
            closest_telemetry = {}
            for tel in reversed(self.telemetry_history):  # Start from most recent
                if tel.get('time', 0) <= time_seconds:
                    closest_telemetry = tel.get('telemetry', {})
                    break
            result['telemetry'] = closest_telemetry
        
        # Find events at or before this time
        if self.event_log:
            relevant_events = []
            for event in self.event_log:
                if event.get('time', 0) <= time_seconds:
                    relevant_events.append(event)
            # Keep last 50 events for display
            result['events'] = relevant_events[-50:] if len(relevant_events) > 50 else relevant_events
        
        # Find operator state at or before this time
        if self.operator_history:
            closest_operator = {}
            for op in reversed(self.operator_history):
                if op.get('time', 0) <= time_seconds:
                    closest_operator = op.get('operator', {})
                    break
            result['operator'] = closest_operator
        
        # Calculate frame index
        if self.fps > 0:
            result['frame_index'] = int(time_seconds * self.fps)
            # Clamp to valid range
            result['frame_index'] = max(0, min(result['frame_index'], self.total_frames - 1))
        
        return result
    
    def update_ui(self, frame: np.ndarray, session_data: Dict[str, Any]):
        """
        Update UI components with current replay data.
        
        Args:
            frame: Current video frame
            session_data: Session data from get_session_data_at_time()
        """
        try:
            # Update dashboard if available
            if self.dashboard:
                # We need to create a snapshot-like object for the dashboard
                # This is simplified - in reality, we'd need to construct proper snapshot
                pass  # Dashboard update would go here
            
            # Update event log
            if self.event_log_ui and session_data['events']:
                # Clear and add events
                self.event_log_ui.state.events.clear()
                for event in session_data['events']:
                    # Convert back to event format expected by EventLog
                    event_copy = event.copy()
                    if 'time' not in event_copy:
                        event_copy['time'] = time.time()
                    self.event_log_ui.state.events.append(event_copy)
            
            # Update telemetry
            if self.telemetry_history_ui and session_data['telemetry']:
                self.telemetry_history_ui.state.telemetry_history.clear()
                sample = {
                    'time': time.time(),
                    'telemetry': session_data['telemetry']
                }
                self.telemetry_history_ui.state.telemetry_history.append(sample)
            
            # Update mission
            if self.mission_state_ui and session_data['mission']:
                self.mission_state_ui.state.mission.update(session_data['mission'])
            
            # Update operator controls
            if self.operator_controls_ui and session_data['operator']:
                self.operator_controls_ui.state.operator.update(session_data['operator'])
                
        except Exception as e:
            Logger.error(f"Error updating UI during replay: {e}")
    
    def get_replay_info(self) -> Dict[str, Any]:
        """
        Get current replay status information.
        
        Returns:
            Dictionary with replay information
        """
        progress_percent = 0.0
        if self.total_frames > 0:
            progress_percent = (self.current_frame_index / self.total_frames) * 100
        
        return {
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'current_frame': self.current_frame_index,
            'total_frames': self.total_frames,
            'progress_percent': progress_percent,
            'fps': self.fps,
            'has_video': self.video_capture is not None and self.video_capture.isOpened(),
            'has_session_data': len(self.telemetry_history) > 0 or len(self.event_log) > 0
        }


# Helper functions for easy integration
def create_replay_system(recordings_folder: str = "recordings", 
                        sessions_folder: str = "sessions") -> SessionReplay:
    """
    Create and return a configured SessionReplay instance.
    
    Args:
        recordings_folder: Folder containing video recordings
        sessions_folder: Folder containing session export files
        
    Returns:
        Configured SessionReplay instance
    """
    return SessionReplay(recordings_folder, sessions_folder)


def format_time(seconds: float) -> str:
    """
    Format seconds as MM:SS or HH:MM:SS.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


# Example usage class for integration with main application
class ReplayController:
    """
    Controller class for integrating replay system with main HuntEye application.
    """
    
    def __init__(self, main_app):
        """
        Initialize replay controller.
        
        Args:
            main_app: Reference to main HuntEye application (for accessing UI components)
        """
        self.main_app = main_app
        self.replay_system = SessionReplay()
        
        # Set up UI components from main app
        self.replay_system.set_ui_components(
            dashboard=getattr(main_app, 'dashboard', None),
            event_log_ui=getattr(main_app, 'event_log', None),
            telemetry_history_ui=getattr(main_app, 'telemetry_history', None),
            mission_state_ui=getattr(main_app, 'mission_state', None),
            operator_controls_ui=getattr(main_app, 'operator_controls', None),
            session_exporter_ui=getattr(main_app, 'exporter', None)
        )
    
    def handle_replay_keypress(self, key: int) -> bool:
        """
        Handle keypress events for replay controls.
        
        Args:
            key: Key code from cv2.waitKey()
            
        Returns:
            True if key was handled by replay system
        """
        if key == ord(' '):  # Spacebar - play/pause
            if self.replay_system.is_playing:
                if self.replay_system.is_paused:
                    self.replay_system.play()
                else:
                    self.replay_system.pause()
            else:
                self.replay_system.play()
            return True
            
        elif key == ord('s'):  # 's' - stop
            self.replay_system.stop()
            return True
            
        elif key == ord('['):  # Left bracket - seek back 10 seconds
            if self.replay_system.is_playing or self.replay_system.total_frames > 0:
                current_time = self.replay_system.current_frame_index / max(self.replay_system.fps, 1)
                new_time = max(0, current_time - 10)
                self.replay_system.seek_to_time(new_time)
            return True
            
        elif key == ord(']'):  # Right bracket - seek forward 10 seconds
            if self.replay_system.is_playing or self.replay_system.total_frames > 0:
                current_time = self.replay_system.current_frame_index / max(self.replay_system.fps, 1)
                new_time = min(self.replay_system.total_frames / max(self.replay_system.fps, 1), 
                             current_time + 10)
                self.replay_system.seek_to_time(new_time)
            return True
            
        elif key == ord(','):  # Comma - frame back
            if self.replay_system.total_frames > 0:
                new_frame = max(0, self.replay_system.current_frame_index - 1)
                self.replay_system.seek_to_frame(new_frame)
            return True
            
        elif key == ord('.'):  # Period - frame forward
            if self.replay_system.total_frames > 0:
                new_frame = min(self.replay_system.total_frames - 1, 
                              self.replay_system.current_frame_index + 1)
                self.replay_system.seek_to_frame(new_frame)
            return True
        
        return False
    
    def get_replay_status_display(self) -> str:
        """
        Get a string for displaying replay status in the UI.
        
        Returns:
            Formatted status string
        """
        info = self.replay_system.get_replay_info()
        
        if not info['has_video']:
            return "No session loaded"
        
        status = "Paused" if info['is_paused'] else ("Playing" if info['is_playing'] else "Stopped")
        time_str = format_time(info['current_frame'] / max(info['fps'], 1))
        total_time_str = format_time(info['total_frames'] / max(info['fps'], 1))
        progress = info['progress_percent']
        
        return f"{status} | {time_str}/{total_time_str} | {progress:.1f}%"