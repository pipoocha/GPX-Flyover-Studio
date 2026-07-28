from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from studio.config.models import ProjectConfig


@dataclass
class Project:
    config: ProjectConfig
    points: list[Any] = field(default_factory=list)
    grid: Any = None
    mesh: Any = None
    sampler: Any = None
    path_coords: Any = None

    @property
    def title(self) -> str:
        return self.config.title

    @property
    def gpx_file(self) -> Path:
        return self.config.gpx.file

    @property
    def video(self):
        return self.config.video

    @property
    def camera(self):
        return self.config.camera

    @property
    def track(self):
        return self.config.track

    @property
    def leader(self):
        return self.config.leader

    @property
    def profile(self):
        return self.config.profile

    @property
    def cinematic(self):
        return self.config.cinematic

    @property
    def terrain(self):
        return self.config.terrain

    @property
    def timeline(self):
        return self.config.timeline
