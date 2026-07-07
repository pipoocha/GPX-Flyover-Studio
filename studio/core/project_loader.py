from pathlib import Path

import yaml

import config
from studio.config_models import (
    ProjectConfig,
    VideoConfig,
    CameraConfig,
    TrackConfig,
)


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

        if "height" in camera_data:
            camera.height = int(camera_data["height"])
        if "distance" in camera_data:
            camera.distance = int(camera_data["distance"])
        if "look_ahead" in camera_data:
            camera.look_ahead = int(camera_data["look_ahead"])
        if "smoothing" in camera_data:
            camera.smoothing = int(camera_data["smoothing"])
        if "focal_height" in camera_data:
            camera.focal_height = int(camera_data["focal_height"])
        if "side_offset" in camera_data:
            camera.side_offset = int(camera_data["side_offset"])

        track = TrackConfig(
            radius=int(track_data.get("radius", config.TRACK_RADIUS)),
            sides=int(track_data.get("sides", config.TRACK_SIDES)),
            progressive=bool(
                track_data.get("progressive", config.TRACE_PROGRESSIVE)
            ),
            update_every=int(
                track_data.get("update_every", config.TRACE_UPDATE_EVERY)
            ),
        )

        project_config = ProjectConfig(
            title=title,
            gpx_file=gpx_file,
            video=video,
            camera=camera,
            track=track,
        )

        project_config.apply()

        return project_config