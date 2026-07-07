from pathlib import Path

import numpy as np
import pyvista as pv

import config
from studio.animation.progress_path import ProgressPath
from studio.animation.timeline import Timeline
from studio.scene.track import Track


class FrameRenderer:
    def __init__(self, scene, camera_path, path_coords, output_dir=None):
        self.scene = scene
        self.camera_path = camera_path
        self.path_coords = path_coords
        self.progress_path = ProgressPath(path_coords)

        self.output_dir = Path(output_dir or config.FRAMES_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.previous_position = None
        self.previous_focal = None

    def clear_frames(self):
        for file in self.output_dir.glob("frame_*.png"):
            file.unlink()

    def smooth_camera(self, position, focal_point, alpha=0.04):
        position = np.asarray(position, dtype=float)
        focal_point = np.asarray(focal_point, dtype=float)

        if self.previous_position is None:
            self.previous_position = position
            self.previous_focal = focal_point
            return position, focal_point

        smoothed_position = self.previous_position * (1.0 - alpha) + position * alpha
        smoothed_focal = self.previous_focal * (1.0 - alpha) + focal_point * alpha

        self.previous_position = smoothed_position
        self.previous_focal = smoothed_focal

        return smoothed_position, smoothed_focal

    def build_track(self, visible_path):
        if config.TRACK_RENDER_MODE == "line":
            return pv.lines_from_points(visible_path)

        return Track(
            visible_path,
            radius=config.TRACK_RADIUS,
            sides=config.TRACK_SIDES,
        ).to_mesh()

    def add_track(self, visible_path):
        mesh = self.build_track(visible_path)

        if config.TRACK_RENDER_MODE == "line":
            return self.scene.add_mesh(
                mesh,
                color="#FC4C02",
                line_width=8,
                render_lines_as_tubes=True,
            )

        return self.scene.add_mesh(
            mesh,
            color="#FC4C02",
            smooth_shading=True,
        )

    def render(self, frames=None):
        total_frames = frames or config.TOTAL_FRAMES
        hold_frames = config.FINAL_HOLD_SECONDS * config.FPS

        timeline = Timeline(
            total_frames=total_frames,
            hold_frames=hold_frames,
            segments=getattr(config, "TIMELINE", []),
        )

        self.clear_frames()

        self.scene.plotter.show(
            auto_close=False,
            interactive=False,
        )

        track_actor = None
        current_camera_label = None

        for i in range(total_frames):
            camera_label = timeline.apply_camera_at(
                frame_index=i,
                fps=config.FPS,
            )

            if camera_label and camera_label != current_camera_label:
                print(f"Caméra : {camera_label}")
                current_camera_label = camera_label

            progress = timeline.progress_at(i)

            position, focal_point, _ = self.camera_path.camera_at_progress(
                progress
            )

            position, focal_point = self.smooth_camera(
                position,
                focal_point,
                alpha=0.04,
            )

            self.scene.plotter.camera_position = [
                tuple(position),
                tuple(focal_point),
                (0, 0, 1),
            ]

            if config.TRACE_PROGRESSIVE:
                if i % config.TRACE_UPDATE_EVERY == 0 or i == total_frames - 1:
                    if timeline.is_hold(i):
                        visible_path = self.path_coords
                    else:
                        visible_path = self.progress_path.visible_path(progress)

                    if track_actor is not None:
                        self.scene.plotter.remove_actor(track_actor)

                    track_actor = self.add_track(visible_path)

            elif track_actor is None:
                track_actor = self.add_track(self.path_coords)

            self.scene.plotter.reset_camera_clipping_range()
            self.scene.plotter.render()
            self.scene.plotter.update()

            file = self.output_dir / f"frame_{i:05d}.png"
            self.scene.plotter.screenshot(str(file))

            if i % 10 == 0 or i == total_frames - 1:
                print(f"Image {i + 1}/{total_frames}")