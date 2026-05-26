"""
Analytics Panel for HuntEye Dashboard (Dev 1.2).

Provides time-series graphing capabilities for visualizing metrics
like FPS, latency, telemetry values over time.
"""

import time
import numpy as np
from collections import deque
from typing import Dict, List, Tuple, Optional, Any
import cv2


class TimeSeries:
    """
    Fixed-size time series data store for plotting.
    """
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.times = deque(maxlen=max_size)
        self.values = deque(maxlen=max_size)
    
    def add(self, timestamp: float, value: float):
        """Add a new data point."""
        self.times.append(timestamp)
        self.values.append(value)
    
    def get_data(self) -> Tuple[List[float], List[float]]:
        """Get times and values as lists."""
        return list(self.times), list(self.values)
    
    def clear(self):
        """Clear all data."""
        self.times.clear()
        self.values.clear()
    
    def __len__(self) -> int:
        return len(self.times)


class AnalyticsPanel:
    """
    Analytics panel for displaying time-series graphs in the dashboard.
    """
    
    def __init__(self, 
                 width: int = 300, 
                 height: int = 200,
                 bg_color: Tuple[int, int, int] = (25, 25, 30),
                 grid_color: Tuple[int, int, int] = (45, 45, 55),
                 axis_color: Tuple[int, int, int] = (80, 80, 90),
                 line_color: Tuple[int, int, int] = (0, 200, 255)):
        """
        Initialize analytics panel.
        
        Args:
            width: Panel width in pixels
            height: Panel height in pixels
            bg_color: Background color (BGR)
            grid_color: Grid line color (BGR)
            axis_color: Axis line color (BGR)
            line_color: Graph line color (BGR)
        """
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.grid_color = grid_color
        self.axis_color = axis_color
        self.line_color = line_color
        
        # Data series storage
        self.series: Dict[str, TimeSeries] = {}
        
        # Display settings
        self.show_grid = True
        self.show_axes = True
        self.show_labels = True
        self.font_scale = 0.4
        self.font_thickness = 1
        
    def add_series(self, name: str, max_size: int = 100):
        """Add a new data series."""
        self.series[name] = TimeSeries(max_size)
    
    def add_point(self, series_name: str, value: float, timestamp: Optional[float] = None):
        """Add a data point to a series."""
        if timestamp is None:
            timestamp = time.time()
        
        if series_name not in self.series:
            self.add_series(series_name)
        
        self.series[series_name].add(timestamp, value)
    
    def clear_series(self, series_name: str):
        """Clear a specific series."""
        if series_name in self.series:
            self.series[series_name].clear()
    
    def clear_all(self):
        """Clear all series."""
        for series in self.series.values():
            series.clear()
    
    def render(self, title: str = "Analytics") -> np.ndarray:
        """
        Render the analytics panel as an image.
        
        Args:
            title: Panel title
            
        Returns:
            Rendered panel as numpy array (BGR format)
        """
        # Create background
        panel = np.full((self.height, self.width, 3), self.bg_color, dtype=np.uint8)
        
        if not self.series:
            # No data to show
            cv2.putText(panel, "No data available", 
                       (10, self.height // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 
                       self.font_scale, (150, 150, 150), 
                       self.font_thickness)
            return panel
        
        # Draw title
        cv2.putText(panel, title, (10, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   self.font_scale + 0.1, (200, 200, 200), 
                   self.font_thickness + 1)
        
        # Calculate plotting area (leave margins for title and labels)
        margin_top = 30
        margin_bottom = 20
        margin_left = 40
        margin_right = 10
        
        plot_width = self.width - margin_left - margin_right
        plot_height = self.height - margin_top - margin_bottom
        
        if plot_width <= 0 or plot_height <= 0:
            return panel
        
        # Draw grid
        if self.show_grid:
            self._draw_grid(panel, margin_left, margin_top, plot_width, plot_height)
        
        # Draw axes
        if self.show_axes:
            self._draw_axes(panel, margin_left, margin_top, plot_width, plot_height)
        
        # Draw data series
        colors = [
            (0, 200, 255),    # Cyan
            (0, 255, 100),    # Green
            (255, 100, 0),    # Orange
            (255, 0, 100),    # Pink
            (100, 0, 255),    # Purple
            (0, 100, 255),    # Blue
        ]
        
        color_index = 0
        for series_name, series in self.series.items():
            if len(series) < 2:
                # Need at least 2 points to draw a line
                continue
                
            color = colors[color_index % len(colors)]
            self._draw_series(panel, series, color, 
                            margin_left, margin_top, plot_width, plot_height)
            color_index += 1
        
        # Draw legend
        self._draw_legend(panel, margin_left, margin_top + plot_height + 5, 
                         self.font_scale, self.font_thickness)
        
        return panel
    
    def _draw_grid(self, panel: np.ndarray, 
                   x_offset: int, y_offset: int, 
                   width: int, height: int):
        """Draw grid lines."""
        # Vertical grid lines
        for i in range(1, 5):
            x = x_offset + (i * width // 5)
            cv2.line(panel, (x, y_offset), (x, y_offset + height), 
                    self.grid_color, 1)
        
        # Horizontal grid lines
        for i in range(1, 5):
            y = y_offset + (i * height // 5)
            cv2.line(panel, (x_offset, y), (x_offset + width, y), 
                    self.grid_color, 1)
    
    def _draw_axes(self, panel: np.ndarray,
                   x_offset: int, y_offset: int,
                   width: int, height: int):
        """Draw X and Y axes."""
        # X axis
        cv2.line(panel, (x_offset, y_offset + height),
                (x_offset + width, y_offset + height),
                self.axis_color, 2)
        
        # Y axis
        cv2.line(panel, (x_offset, y_offset),
                (x_offset, y_offset + height),
                self.axis_color, 2)
    
    def _draw_series(self, panel: np.ndarray,
                    series: TimeSeries,
                    color: Tuple[int, int, int],
                    x_offset: int, y_offset: int,
                    width: int, height: int):
        """Draw a data series as a line graph."""
        times, values = series.get_data()
        
        if len(times) < 2:
            return
        
        # Normalize times to [0, 1] range for x-axis
        if len(times) > 1:
            time_range = max(times) - min(times)
            if time_range > 0:
                norm_times = [(t - min(times)) / time_range for t in times]
            else:
                norm_times = [0.0] * len(times)
        else:
            norm_times = [0.0]
        
        # Normalize values to [0, 1] range for y-axis (inverted for image coords)
        if len(values) > 1:
            min_val = min(values)
            max_val = max(values)
            value_range = max_val - min_val
            if value_range > 0:
                norm_values = [(v - min_val) / value_range for v in values]
            else:
                norm_values = [0.5] * len(values)  # Center if all same value
        else:
            norm_values = [0.5]
        
        # Convert to pixel coordinates
        points = []
        for i, (norm_t, norm_v) in enumerate(zip(norm_times, norm_values)):
            x = x_offset + int(norm_t * width)
            y = y_offset + height - int(norm_v * height)  # Flip Y for image coords
            points.append((x, y))
        
        # Draw lines between points
        if len(points) >= 2:
            for i in range(len(points) - 1):
                cv2.line(panel, points[i], points[i + 1], color, 2)
        
        # Draw points
        for point in points:
            cv2.circle(panel, point, 2, color, -1)
    
    def _draw_legend(self, panel: np.ndarray,
                    x_offset: int, y_offset: int,
                    font_scale: float, font_thickness: int):
        """Draw legend for data series."""
        colors = [
            (0, 200, 255),    # Cyan
            (0, 255, 100),    # Green
            (255, 100, 0),    # Orange
            (255, 0, 100),    # Pink
            (100, 0, 255),    # Purple
            (0, 100, 255),    # Blue
        ]
        
        legend_x = x_offset + 10
        legend_y = y_offset
        line_height = int(20 * font_scale)
        
        for i, (series_name, series) in enumerate(self.series.items()):
            if i >= len(colors):
                break
                
            color = colors[i % len(colors)]
            
            # Draw color sample
            cv2.rectangle(panel, 
                         (legend_x, legend_y + i * line_height),
                         (legend_x + 12, legend_y + i * line_height + 12),
                         color, -1)
            cv2.rectangle(panel,
                         (legend_x, legend_y + i * line_height),
                         (legend_x + 12, legend_y + i * line_height + 12),
                         (50, 50, 50), 1)
            
            # Draw series name and current value
            text = f"{series_name}: {list(series.values)[-1] if series.values else 0:.2f}"
            cv2.putText(panel, text,
                       (legend_x + 20, legend_y + i * line_height + 10),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       font_scale, (200, 200, 200), font_thickness)


# Example usage helper for integration with dashboard
def create_fps_analytics_panel(width: int = 300, height: int = 150) -> AnalyticsPanel:
    """Create an analytics panel specifically for FPS monitoring."""
    panel = AnalyticsPanel(width=width, height=height,
                          bg_color=(20, 20, 25),
                          grid_color=(40, 40, 50),
                          axis_color=(80, 80, 90),
                          line_color=(0, 255, 100))
    panel.add_series("FPS", max_size=100)
    return panel


def create_latency_analytics_panel(width: int = 300, height: int = 150) -> AnalyticsPanel:
    """Create an analytics panel specifically for latency monitoring."""
    panel = AnalyticsPanel(width=width, height=height,
                          bg_color=(20, 20, 25),
                          grid_color=(40, 40, 50),
                          axis_color=(80, 80, 90),
                          line_color=(0, 200, 255))
    panel.add_series("Latency (ms)", max_size=100)
    return panel