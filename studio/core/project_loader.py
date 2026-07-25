from pathlib import Path

import yaml

import config
from studio.config_models import (
    ProjectConfig,
    VideoConfig,
    CameraConfig,
    TrackConfig,
)
from studio.track.presets import get_track_preset


class ProjectLoader:
    def __init__(self, project_file):
        self.project_file = Path(project_file)

    @staticmethod
    def apply_config_values(source, mapping):
        for yaml_key, config_name, converter, default in mapping:
            value = source.get(yaml_key, default)
            setattr(config, config_name, converter(value))

    def load(self):
        if not self.project_file.exists():
            raise FileNotFoundError(f"Projet introuvable : {self.project_file}")

        with open(self.project_file, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        project_data = data.get("project", {})
        gpx_data = data.get("gpx", {})
        video_data = data.get("video", {})
        camera_data = data.get("camera", {})
        track_data = data.get("track", {})
        leader_data = data.get("leader", {})
        terrain_data = data.get("terrain", {})
        outro_data = data.get("outro", {})
        timeline_data = data.get("timeline", [])

        title = project_data.get("title", config.PROJECT_TITLE)
        gpx_file = Path(gpx_data.get("file", config.DEFAULT_GPX))

        width = config.WINDOW_WIDTH
        height = config.WINDOW_HEIGHT
        if "size" in video_data:
            width_text, height_text = str(video_data["size"]).lower().split("x")
            width = int(width_text)
            height = int(height_text)

        video = VideoConfig(
            mode=str(video_data.get("mode", config.MODE)).upper(),
            duration=int(video_data.get("duration", config.VIDEO_DURATION)),
            final_hold_seconds=int(video_data.get("final_hold_seconds", 0)),
            fps=int(video_data.get("fps", config.FPS)),
            width=width,
            height=height,
            output=Path(video_data.get("output", config.DEFAULT_VIDEO)),
        )

        camera_preset = str(camera_data.get("preset", "cinematic")).lower()
        config.CAMERA_PRESET = camera_preset
        camera = CameraConfig.from_preset(camera_preset)

        for key in (
            "height",
            "distance",
            "look_ahead",
            "smoothing",
            "focal_height",
            "side_offset",
        ):
            if key in camera_data:
                setattr(camera, key, int(camera_data[key]))

        config.CAMERA_MODE = str(camera_data.get("mode", "director")).lower()

        orientation_data = camera_data.get("orientation", {})
        if isinstance(orientation_data, str):
            config.CAMERA_ORIENTATION_MODE = orientation_data.lower()
            config.CAMERA_ORIENTATION_ANGLE = 0.0
        elif isinstance(orientation_data, dict):
            config.CAMERA_ORIENTATION_MODE = str(
                orientation_data.get("mode", "auto")
            ).lower()
            config.CAMERA_ORIENTATION_ANGLE = float(
                orientation_data.get("angle", 0.0)
            )
        else:
            config.CAMERA_ORIENTATION_MODE = "auto"
            config.CAMERA_ORIENTATION_ANGLE = 0.0

        camera_mapping = (
            ("local_fit_distance_scale", "CAMERA_LOCAL_FIT_DISTANCE_SCALE", float, 0.40),
            ("local_fit_height_scale", "CAMERA_LOCAL_FIT_HEIGHT_SCALE", float, 0.20),
            ("local_fit_min_distance", "CAMERA_LOCAL_FIT_MIN_DISTANCE", float, 1200.0),
            ("local_fit_max_distance", "CAMERA_LOCAL_FIT_MAX_DISTANCE", float, 3600.0),
            ("local_fit_min_height", "CAMERA_LOCAL_FIT_MIN_HEIGHT", float, 600.0),
            ("local_fit_max_height", "CAMERA_LOCAL_FIT_MAX_HEIGHT", float, 1900.0),
            ("lateral_distance_scale", "CAMERA_LATERAL_DISTANCE_SCALE", float, 0.12),
            ("lateral_minimum", "CAMERA_LATERAL_MINIMUM", float, 160.0),
            ("lateral_maximum", "CAMERA_LATERAL_MAXIMUM", float, 700.0),
            ("endpoint_window", "CAMERA_ENDPOINT_WINDOW", float, 0.08),
        )
        self.apply_config_values(camera_data, camera_mapping)

        track_preset = {}
        if "preset" in track_data:
            track_preset = get_track_preset(str(track_data["preset"]).lower())

        radius = int(track_data.get("radius", track_preset.get("radius", config.TRACK_RADIUS)))
        sides = int(track_data.get("sides", track_preset.get("sides", config.TRACK_SIDES)))
        progressive = bool(
            track_data.get(
                "progressive",
                track_preset.get("progressive", config.TRACE_PROGRESSIVE),
            )
        )
        update_every = int(
            track_data.get(
                "update_every",
                track_preset.get("update_every", config.TRACE_UPDATE_EVERY),
            )
        )
        render_mode = str(
            track_data.get(
                "render_mode",
                track_preset.get("render_mode", config.TRACK_RENDER_MODE),
            )
        ).lower()

        track = TrackConfig(
            radius=radius,
            sides=sides,
            progressive=progressive,
            update_every=update_every,
        )

        config.TRACK_RENDER_MODE = render_mode
        config.TRACK_LINE_WIDTH = float(track_data.get("line_width", 1.5))
        config.TRACK_Z_OFFSET = float(track_data.get("z_offset", 8.0))
        config.TRACK_COLOR = str(track_data.get("color", "#FC4C02"))
        config.START_VISIBLE_SEGMENTS = int(
            track_data.get("start_visible_segments", 12)
        )

        config.LEADER_ENABLED = bool(leader_data.get("enabled", False))
        config.LEADER_STYLE = str(leader_data.get("style", "glow")).lower()
        config.LEADER_RADIUS = float(leader_data.get("radius", 12.0))
        config.LEADER_Z_OFFSET = float(leader_data.get("z_offset", 10.0))
        config.LEADER_COLOR = str(leader_data.get("color", config.TRACK_COLOR))
        config.LEADER_HALO_SCALE = float(leader_data.get("halo_scale", 1.6))
        config.LEADER_HALO_OPACITY = float(leader_data.get("halo_opacity", 0.16))

        terrain_mapping = (
            ("source", "TERRAIN_SOURCE", str, "copernicus"),
            ("copernicus_margin", "COPERNICUS_MARGIN", float, 0.006),
            ("copernicus_max_cells", "COPERNICUS_MAX_CELLS", int, 60000),
            ("use_satellite", "USE_SATELLITE", bool, True),
            ("satellite_zoom", "SATELLITE_ZOOM", int, 14),
            ("satellite_flip_vertical", "SATELLITE_FLIP_VERTICAL", bool, True),
        )
        self.apply_config_values(terrain_data, terrain_mapping)

        outro_mapping = (
            ("start_hold_seconds", "START_HOLD_SECONDS", float, 3.0),
            ("arrival_hold_seconds", "ARRIVAL_HOLD_SECONDS", float, 5.0),
            ("flatten_transition_seconds", "FLATTEN_TRANSITION_SECONDS", float, 3.0),
            ("profile_animation_seconds", "PROFILE_ANIMATION_SECONDS", float, 6.0),
            ("profile_hold_seconds", "PROFILE_HOLD_SECONDS", float, 4.0),
            ("travel_ease_strength", "TRAVEL_EASE_STRENGTH", float, 1.0),
            ("start_camera_progress", "START_CAMERA_PROGRESS", float, 0.004),
            ("profile_inset_width_ratio", "PROFILE_INSET_WIDTH_RATIO", float, 0.40),
            ("profile_inset_height_ratio", "PROFILE_INSET_HEIGHT_RATIO", float, 0.30),
            ("profile_inset_margin", "PROFILE_INSET_MARGIN", int, 24),
            ("profile_inset_corner", "PROFILE_INSET_CORNER", str, "bottom_right"),
            ("final_topdown_height_scale", "FINAL_TOPDOWN_HEIGHT_SCALE", float, 1.10),
            ("final_topdown_min_height", "FINAL_TOPDOWN_MIN_HEIGHT", float, 2500.0),
        )
        self.apply_config_values(outro_data, outro_mapping)

        project_config = ProjectConfig(
            title=title,
            gpx_file=gpx_file,
            video=video,
            camera=camera,
            track=track,
        )

        project_config.apply()

        # Réapplique les valeurs qui ne font pas partie des anciens modèles.
        config.TRACK_RENDER_MODE = render_mode
        config.TIMELINE = timeline_data or []

        return project_config
