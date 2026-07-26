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
    def __init__(
        self,
        project_file,
    ):
        self.project_file = Path(
            project_file
        )

    def load(self):
        if not self.project_file.exists():
            raise FileNotFoundError(
                f"Projet introuvable : "
                f"{self.project_file}"
            )

        with open(
            self.project_file,
            "r",
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(file) or {}

        project_data = data.get(
            "project",
            {},
        )

        gpx_data = data.get(
            "gpx",
            {},
        )

        video_data = data.get(
            "video",
            {},
        )

        camera_data = data.get(
            "camera",
            {},
        )

        track_data = data.get(
            "track",
            {},
        )

        leader_data = data.get(
            "leader",
            {},
        )

        timeline_data = data.get(
            "timeline",
            [],
        )

        title = project_data.get(
            "title",
            config.PROJECT_TITLE,
        )

        gpx_file = Path(
            gpx_data.get(
                "file",
                config.DEFAULT_GPX,
            )
        )

        width = config.WINDOW_WIDTH
        height = config.WINDOW_HEIGHT

        if "size" in video_data:
            (
                width_text,
                height_text,
            ) = str(
                video_data["size"]
            ).lower().split("x")

            width = int(width_text)
            height = int(height_text)

        video = VideoConfig(
            mode=str(
                video_data.get(
                    "mode",
                    config.MODE,
                )
            ).upper(),
            duration=int(
                video_data.get(
                    "duration",
                    config.VIDEO_DURATION,
                )
            ),
            final_hold_seconds=int(
                video_data.get(
                    "final_hold_seconds",
                    config.FINAL_HOLD_SECONDS,
                )
            ),
            fps=int(
                video_data.get(
                    "fps",
                    config.FPS,
                )
            ),
            width=width,
            height=height,
            output=Path(
                video_data.get(
                    "output",
                    config.DEFAULT_VIDEO,
                )
            ),
        )

        camera_preset = str(
            camera_data.get(
                "preset",
                "cinematic",
            )
        ).lower()

        config.CAMERA_PRESET = (
            camera_preset
        )

        camera = (
            CameraConfig.from_preset(
                camera_preset
            )
        )

        for key in (
            "height",
            "distance",
            "look_ahead",
            "smoothing",
            "focal_height",
            "side_offset",
        ):
            if key in camera_data:
                setattr(
                    camera,
                    key,
                    int(camera_data[key]),
                )

        config.CAMERA_MODE = str(
            camera_data.get(
                "mode",
                "flyover",
            )
        ).lower()

        orientation_data = (
            camera_data.get(
                "orientation",
                {},
            )
        )

        if isinstance(
            orientation_data,
            str,
        ):
            config.CAMERA_ORIENTATION_MODE = (
                orientation_data.lower()
            )

            config.CAMERA_ORIENTATION_ANGLE = (
                0.0
            )

        elif isinstance(
            orientation_data,
            dict,
        ):
            config.CAMERA_ORIENTATION_MODE = str(
                orientation_data.get(
                    "mode",
                    "route",
                )
            ).lower()

            config.CAMERA_ORIENTATION_ANGLE = float(
                orientation_data.get(
                    "angle",
                    0,
                )
            )

        else:
            config.CAMERA_ORIENTATION_MODE = (
                "route"
            )

            config.CAMERA_ORIENTATION_ANGLE = (
                0.0
            )

        if "preset" in track_data:
            track_preset = (
                get_track_preset(
                    str(
                        track_data["preset"]
                    ).lower()
                )
            )
        else:
            track_preset = {}

        radius = int(
            track_data.get(
                "radius",
                track_preset.get(
                    "radius",
                    config.TRACK_RADIUS,
                ),
            )
        )

        sides = int(
            track_data.get(
                "sides",
                track_preset.get(
                    "sides",
                    config.TRACK_SIDES,
                ),
            )
        )

        progressive = bool(
            track_data.get(
                "progressive",
                track_preset.get(
                    "progressive",
                    config.TRACE_PROGRESSIVE,
                ),
            )
        )

        update_every = int(
            track_data.get(
                "update_every",
                track_preset.get(
                    "update_every",
                    config.TRACE_UPDATE_EVERY,
                ),
            )
        )

        render_mode = str(
            track_data.get(
                "render_mode",
                track_preset.get(
                    "render_mode",
                    config.TRACK_RENDER_MODE,
                ),
            )
        ).lower()

        track = TrackConfig(
            radius=radius,
            sides=sides,
            progressive=progressive,
            update_every=update_every,
        )

        config.LEADER_ENABLED = bool(
            leader_data.get(
                "enabled",
                config.LEADER_ENABLED,
            )
        )

        config.LEADER_STYLE = str(
            leader_data.get(
                "style",
                config.LEADER_STYLE,
            )
        ).lower()

        config.LEADER_RADIUS = float(
            leader_data.get(
                "radius",
                config.LEADER_RADIUS,
            )
        )

        config.LEADER_Z_OFFSET = float(
            leader_data.get(
                "z_offset",
                config.LEADER_Z_OFFSET,
            )
        )

        config.LEADER_COLOR = str(
            leader_data.get(
                "color",
                config.LEADER_COLOR,
            )
        )

        config.LEADER_HALO_SCALE = float(
            leader_data.get(
                "halo_scale",
                config.LEADER_HALO_SCALE,
            )
        )

        config.LEADER_HALO_OPACITY = float(
            leader_data.get(
                "halo_opacity",
                config.LEADER_HALO_OPACITY,
            )
        )

        project_config = ProjectConfig(
            title=title,
            gpx_file=gpx_file,
            video=video,
            camera=camera,
            track=track,
        )

        project_config.apply()

        config.TRACK_RENDER_MODE = (
            render_mode
        )

        config.TIMELINE = (
            timeline_data or []
        )

        return project_config