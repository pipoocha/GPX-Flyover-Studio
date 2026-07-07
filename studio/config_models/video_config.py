from dataclasses import dataclass
from pathlib import Path

import config


@dataclass
class VideoConfig:
    mode: str = "DEV"
    duration: int = 30
    final_hold_seconds: int = 5
    fps: int = 20
    width: int = 854
    height: int = 480
    output: Path = config.DEFAULT_VIDEO

    @property
    def total_frames(self):
        return self.duration * self.fps

    def apply(self):
        config.MODE = self.mode
        config.VIDEO_DURATION = self.duration
        config.FINAL_HOLD_SECONDS = self.final_hold_seconds
        config.FPS = self.fps
        config.TOTAL_FRAMES = self.total_frames
        config.WINDOW_WIDTH = self.width
        config.WINDOW_HEIGHT = self.height
        config.DEFAULT_VIDEO = self.output