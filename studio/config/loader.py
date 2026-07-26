from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from studio.config.defaults import DEFAULT_CONFIG
from studio.config.models import (
    CameraConfig,
    CameraRange,
    GPXConfig,
    ProjectConfig,
    TerrainConfig,
    TimelineConfig,
    TrackConfig,
    VideoConfig,
)
from studio.config.validator import validate_project


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ProjectLoaderV5:
    def __init__(self, project_file: str | Path):
        self.project_file = Path(project_file)

    @staticmethod
    def parse_resolution(value: str) -> tuple[int, int]:
        try:
            width_text, height_text = str(value).lower().split("x", 1)
            return int(width_text), int(height_text)
        except Exception as error:
            raise ValueError(f"Résolution invalide : {value}") from error

    def load(self, require_existing_gpx: bool = False) -> ProjectConfig:
        if not self.project_file.exists():
            raise FileNotFoundError(f"Projet introuvable : {self.project_file}")

        raw = yaml.safe_load(self.project_file.read_text(encoding="utf-8")) or {}
        data = deep_merge(DEFAULT_CONFIG, raw)

        camera = data["camera"]
        track = data["track"]
        terrain = data["terrain"]
        timeline = data["timeline"]
        video = data["video"]
        width, height = self.parse_resolution(video["resolution"])

        project = ProjectConfig(
            title=str(data["project"]["title"]),
            gpx=GPXConfig(file=Path(data["gpx"]["file"])),
            camera=CameraConfig(
                mode=str(camera["mode"]).lower(),
                orientation=str(camera["orientation"]).lower(),
                distance=CameraRange(
                    minimum=float(camera["distance"]["min"]),
                    maximum=float(camera["distance"]["max"]),
                    scale=float(camera["distance"]["scale"]),
                ),
                height=CameraRange(
                    minimum=float(camera["height"]["min"]),
                    maximum=float(camera["height"]["max"]),
                    scale=float(camera["height"]["scale"]),
                ),
                lateral=CameraRange(
                    minimum=float(camera["lateral"]["min"]),
                    maximum=float(camera["lateral"]["max"]),
                    scale=float(camera["lateral"]["scale"]),
                ),
                look_ahead=int(camera["look_ahead"]),
                smoothing=float(camera["smoothing"]),
            ),
            track=TrackConfig(
                color=str(track["color"]),
                width=float(track["width"]),
                z_offset=float(track["z_offset"]),
                progressive=bool(track["progressive"]),
                leader=bool(track["leader"]),
            ),
            terrain=TerrainConfig(
                source=str(terrain["source"]).lower(),
                satellite=bool(terrain["satellite"]),
                satellite_zoom=int(terrain["satellite_zoom"]),
                max_cells=int(terrain["max_cells"]),
                margin=float(terrain["margin"]),
            ),
            timeline=TimelineConfig(
                speed=float(timeline["speed"]),
                intro=float(timeline["intro"]),
                zoom_to_start=float(timeline["zoom_to_start"]),
                start_hold=float(timeline["start_hold"]),
                travel=float(timeline["travel"]),
                slowdown_start=float(timeline["slowdown_start"]),
                slowdown_end=float(timeline["slowdown_end"]),
                arrival_hold=float(timeline["arrival_hold"]),
                flatten=float(timeline["flatten"]),
                profile_animation=float(timeline["profile_animation"]),
                profile_hold=float(timeline["profile_hold"]),
                fade_out=float(timeline["fade_out"]),
            ),
            video=VideoConfig(
                fps=int(video["fps"]),
                width=width,
                height=height,
                output=Path(video["output"]),
                mode=str(video["mode"]).upper(),
            ),
            source_file=self.project_file,
        )

        validate_project(project, require_existing_gpx=require_existing_gpx)
        return project

    @staticmethod
    def save(project: ProjectConfig, project_file: str | Path | None = None) -> Path:
        target = Path(project_file or project.source_file or "projects/project_v5.yaml")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            yaml.safe_dump(
                project.to_dict(),
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        project.source_file = target
        return target
