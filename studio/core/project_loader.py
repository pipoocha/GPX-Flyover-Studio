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

    def load(self):
        if not self.project_file.exists():
            raise FileNotFoundError(f"Projet introuvable : {self.project_file}")

        with open(self.project_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        project_data = data.get("project", {})
        gpx_data = data.get("gpx", {})
        video_data = data.get("video", {})
        camera_data = data.get("camera", {})
        track_data = data.get("track", {})
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
            final_hold_seconds=int(
                video_data.get("final_hold_seconds", config.FINAL_HOLD_SECONDS)
            ),
            fps=int(video_data.get("fps", config.FPS)),
            width=width,
            height=height,
            output=Path(video_data.get("output", config.DEFAULT_VIDEO)),
        )

        if "preset" in camera_data:
            camera = CameraConfig.from_preset(
                str(camera_data["preset"]).lower()
            )
        else:
            camera = CameraConfig()

        for key in [
            "height",
            "distance",
            "look_ahead",
            "smoothing",
            "focal_height",
            "side_offset",
        ]:
            if key in camera_data:
                setattr(camera, key, int(camera_data[key]))

        config.CAMERA_MODE = str(
            camera_data.get("mode", "flyover")
        ).lower()

        orientation_data = camera_data.get("orientation", {})

        if isinstance(orientation_data, str):
            config.CAMERA_ORIENTATION_MODE = orientation_data.lower()
            config.CAMERA_ORIENTATION_ANGLE = 0
        elif isinstance(orientation_data, dict):
            config.CAMERA_ORIENTATION_MODE = str(
                orientation_data.get("mode", "route")
            ).lower()
            config.CAMERA_ORIENTATION_ANGLE = float(
                orientation_data.get("angle", 0)
            )
        else:
            config.CAMERA_ORIENTATION_MODE = "route"
            config.CAMERA_ORIENTATION_ANGLE = 0

        if "preset" in track_data:
            preset = get_track_preset(
                str(track_data["preset"]).lower()
            )
        else:
            preset = {}

        radius = int(track_data.get("radius", preset.get("radius", config.TRACK_RADIUS)))
        sides = int(track_data.get("sides", preset.get("sides", config.TRACK_SIDES)))
        progressive = bool(
            track_data.get(
                "progressive",
                preset.get("progressive", config.TRACE_PROGRESSIVE),
            )
        )
        update_every = int(
            track_data.get(
                "update_every",
                preset.get("update_every", config.TRACE_UPDATE_EVERY),
            )
        )

        render_mode = str(
            track_data.get(
                "render_mode",
                preset.get("render_mode", config.TRACK_RENDER_MODE),
            )
        ).lower()

        track = TrackConfig(
            radius=radius,
            sides=sides,
            progressive=progressive,
            update_every=update_every,
        )

        project_config = ProjectConfig(
            title=title,
            gpx_file=gpx_file,
            video=video,
            camera=camera,
            track=track,
        )

        project_config.apply()

        config.TRACK_RENDER_MODE = render_mode
        config.TIMELINE = timeline_data or []

        return project_config