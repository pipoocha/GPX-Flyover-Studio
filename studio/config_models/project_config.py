from dataclasses import dataclass
from pathlib import Path

import config
from studio.config_models.video_config import VideoConfig
from studio.config_models.camera_config import CameraConfig
from studio.config_models.track_config import TrackConfig


@dataclass
class ProjectConfig:
    title: str
    gpx_file: Path
    video: VideoConfig
    camera: CameraConfig
    track: TrackConfig

    def apply(self):
        config.PROJECT_TITLE = self.title
        self.video.apply()
        self.camera.apply()
        self.track.apply()