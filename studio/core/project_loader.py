from pathlib import Path

import yaml

import config


class ProjectLoader:
    def __init__(self, project_file):
        self.project_file = Path(project_file)

    def load(self):
        if not self.project_file.exists():
            raise FileNotFoundError(f"Projet introuvable : {self.project_file}")

        with open(self.project_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        project = data.get("project", {})
        gpx = data.get("gpx", {})
        video = data.get("video", {})
        camera = data.get("camera", {})
        track = data.get("track", {})

        if "title" in project:
            config.PROJECT_TITLE = project["title"]

        if "mode" in video:
            config.MODE = str(video["mode"]).upper()

        if "duration" in video:
            config.VIDEO_DURATION = int(video["duration"])

        if "fps" in video:
            config.FPS = int(video["fps"])

        config.TOTAL_FRAMES = config.VIDEO_DURATION * config.FPS

        if "size" in video:
            width, height = str(video["size"]).lower().split("x")
            config.WINDOW_WIDTH = int(width)
            config.WINDOW_HEIGHT = int(height)

        if "output" in video:
            config.DEFAULT_VIDEO = Path(video["output"])

        if "height" in camera:
            config.CAMERA_HEIGHT = int(camera["height"])

        if "distance" in camera:
            config.CAMERA_DISTANCE = int(camera["distance"])

        if "look_ahead" in camera:
            config.LOOK_AHEAD = int(camera["look_ahead"])

        if "smoothing" in camera:
            config.CAMERA_SMOOTHING = int(camera["smoothing"])

        if "focal_height" in camera:
            config.FOCAL_HEIGHT = int(camera["focal_height"])

        if "side_offset" in camera:
            config.SIDE_OFFSET = int(camera["side_offset"])

        if "radius" in track:
            config.TRACK_RADIUS = int(track["radius"])

        if "sides" in track:
            config.TRACK_SIDES = int(track["sides"])

        if "progressive" in track:
            config.TRACE_PROGRESSIVE = bool(track["progressive"])

        if "update_every" in track:
            config.TRACE_UPDATE_EVERY = int(track["update_every"])

        gpx_file = gpx.get("file", config.DEFAULT_GPX)

        return Path(gpx_file)