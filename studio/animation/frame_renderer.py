from pathlib import Path

import numpy as np
import pyvista as pv

import config
from studio.animation.progress_path import ProgressPath
from studio.animation.timeline import Timeline
from studio.leader.leader import LeaderMarker
from studio.scene.track import Track


class FrameRenderer:
    def __init__(
        self,
        scene,
        camera_path,
        path_coords,
        output_dir=None,
    ):
        self.scene = scene
        self.camera_path = camera_path
        self.path_coords = np.asarray(
            path_coords,
            dtype=float,
        )

        self.progress_path = ProgressPath(
            self.path_coords
        )

        self.output_dir = Path(
            output_dir or config.FRAMES_DIR
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.previous_position = None
        self.previous_focal = None

        self.track_actor = None
        self.leader = LeaderMarker(
            scene=self.scene,
            path_coords=self.path_coords,
        )

    def clear_frames(self):
        for file in self.output_dir.glob(
            "frame_*.png"
        ):
            file.unlink()

    def smooth_camera(
        self,
        position,
        focal_point,
        alpha=0.04,
    ):
        position = np.asarray(
            position,
            dtype=float,
        )

        focal_point = np.asarray(
            focal_point,
            dtype=float,
        )

        if self.previous_position is None:
            self.previous_position = position
            self.previous_focal = focal_point

            return position, focal_point

        smoothed_position = (
            self.previous_position * (1.0 - alpha)
            + position * alpha
        )

        smoothed_focal = (
            self.previous_focal * (1.0 - alpha)
            + focal_point * alpha
        )

        self.previous_position = smoothed_position
        self.previous_focal = smoothed_focal

        return smoothed_position, smoothed_focal

    def build_track_mesh(self, visible_path):
        render_mode = getattr(
            config,
            "TRACK_RENDER_MODE",
            "line",
        )

        if render_mode == "line":
            return pv.lines_from_points(
                visible_path
            )

        return Track(
            visible_path,
            radius=config.TRACK_RADIUS,
            sides=config.TRACK_SIDES,
        ).to_mesh()

    def add_track_actor(self, visible_path):
        mesh = self.build_track_mesh(
            visible_path
        )

        render_mode = getattr(
            config,
            "TRACK_RENDER_MODE",
            "line",
        )

        if render_mode == "line":
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

    def update_track(
        self,
        progress,
        force=False,
        frame_index=0,
    ):
        update_every = max(
            1,
            int(
                getattr(
                    config,
                    "TRACE_UPDATE_EVERY",
                    5,
                )
            ),
        )

        if (
            not force
            and frame_index % update_every != 0
        ):
            return

        if getattr(
            config,
            "TRACE_PROGRESSIVE",
            True,
        ):
            visible_path = (
                self.progress_path.visible_path(
                    progress
                )
            )
        else:
            visible_path = self.path_coords

        if len(visible_path) < 2:
            return

        plotter = self.scene.plotter

        if self.track_actor is not None:
            plotter.remove_actor(
                self.track_actor,
                render=False,
            )

        self.track_actor = self.add_track_actor(
            visible_path
        )

    def render(self, frames=None):
        total_frames = int(
            frames or config.TOTAL_FRAMES
        )

        hold_frames = (
            config.FINAL_HOLD_SECONDS
            * config.FPS
        )

        timeline = Timeline(
            total_frames=total_frames,
            hold_frames=hold_frames,
            segments=getattr(
                config,
                "TIMELINE",
                [],
            ),
        )

        self.clear_frames()

        self.scene.plotter.show(
            auto_close=False,
            interactive=False,
        )

        self.leader.create()

        current_camera_label = None

        for frame_index in range(total_frames):
            camera_label = (
                timeline.apply_camera_at(
                    frame_index=frame_index,
                    fps=config.FPS,
                )
            )

            if (
                camera_label
                and camera_label
                != current_camera_label
            ):
                print(
                    f"Caméra : {camera_label}"
                )
                current_camera_label = (
                    camera_label
                )

            progress = timeline.progress_at(
                frame_index
            )

            position, focal_point, _ = (
                self.camera_path.camera_at_progress(
                    progress
                )
            )

            position, focal_point = (
                self.smooth_camera(
                    position,
                    focal_point,
                    alpha=0.04,
                )
            )

            self.scene.plotter.camera_position = [
                tuple(position),
                tuple(focal_point),
                (0, 0, 1),
            ]

            self.update_track(
                progress=progress,
                force=frame_index == 0,
                frame_index=frame_index,
            )

            self.leader.update(progress)

            plotter = self.scene.plotter

            plotter.reset_camera_clipping_range()
            plotter.render()
            plotter.update()

            output_file = (
                self.output_dir
                / f"frame_{frame_index:05d}.png"
            )

            plotter.screenshot(
                str(output_file)
            )

            if (
                frame_index % 10 == 0
                or frame_index
                == total_frames - 1
            ):
                print(
                    f"Image "
                    f"{frame_index + 1}/"
                    f"{total_frames}"
                )