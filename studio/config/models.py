from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GPXConfig:
    file: Path

    def to_dict(self) -> dict[str, Any]:
        return {"file": self.file.as_posix()}


@dataclass
class CameraRange:
    minimum: float
    maximum: float
    scale: float

    def to_dict(self) -> dict[str, float]:
        return {
            "min": float(self.minimum),
            "max": float(self.maximum),
            "scale": float(self.scale),
        }


@dataclass
class CameraConfig:
    mode: str
    orientation: str
    distance: CameraRange
    height: CameraRange
    lateral: CameraRange
    look_ahead: int
    smoothing: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "orientation": self.orientation,
            "distance": self.distance.to_dict(),
            "height": self.height.to_dict(),
            "lateral": self.lateral.to_dict(),
            "look_ahead": int(self.look_ahead),
            "smoothing": float(self.smoothing),
        }


@dataclass
class TrackConfig:
    color: str
    width: float
    z_offset: float
    progressive: bool
    leader: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LeaderConfig:
    """Réglages persistants du leader lumineux."""

    enabled: bool
    style: str
    color: str
    radius: float
    z_offset: float
    halo_scale: float
    halo_opacity: float
    trail_enabled: bool
    trail_fraction: float
    trail_width: float
    trail_opacity: float
    fade_trail_on_arrival: bool
    trail_fade_duration: float
    screen_space_enabled: bool
    reference_distance: float
    minimum_scale: float
    maximum_scale: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProfileSelectionConfig:
    selected: str = ""
    recommended: str = ""
    confidence: float = 0.0
    source: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CinematicConfig:
    start_centered: bool = True
    start_zoom: float = 0.45
    start_transition: float = 3.0
    finish_zoom: float = 0.70

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TerrainConfig:
    source: str
    satellite: bool
    satellite_zoom: int
    max_cells: int
    margin: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineConfig:
    speed: float
    intro: float
    zoom_to_start: float
    start_hold: float
    travel: float
    slowdown_start: float
    slowdown_end: float
    arrival_hold: float
    flatten: float
    profile_animation: float
    profile_hold: float
    fade_out: float

    @property
    def effective_travel(self) -> float:
        return float(self.travel / max(0.05, self.speed))

    @property
    def total_duration(self) -> float:
        values = asdict(self)
        values.pop("speed", None)
        values["travel"] = self.effective_travel
        return float(sum(values.values()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VideoConfig:
    fps: int
    width: int
    height: int
    output: Path
    mode: str

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "fps": int(self.fps),
            "resolution": self.resolution,
            "output": self.output.as_posix(),
            "mode": self.mode,
        }


@dataclass
class ProjectConfig:
    title: str
    gpx: GPXConfig
    camera: CameraConfig
    track: TrackConfig
    leader: LeaderConfig
    profile: ProfileSelectionConfig
    cinematic: CinematicConfig
    terrain: TerrainConfig
    timeline: TimelineConfig
    video: VideoConfig
    source_file: Path | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": {"title": self.title},
            "gpx": self.gpx.to_dict(),
            "camera": self.camera.to_dict(),
            "track": self.track.to_dict(),
            "leader": self.leader.to_dict(),
            "profile": self.profile.to_dict(),
            "cinematic": self.cinematic.to_dict(),
            "terrain": self.terrain.to_dict(),
            "timeline": self.timeline.to_dict(),
            "video": self.video.to_dict(),
        }
