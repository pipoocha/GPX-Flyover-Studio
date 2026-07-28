import time

import numpy as np
import pyvista as pv

import config
from studio.animation.progress_path import ProgressPath
from studio.leader.leader import LeaderMarker


class PreviewPlayer:
    """Preview interactif optimisé avec trace persistante."""

    def __init__(self, scene, camera_path, path_coords, frames=300, fps=None):
        self.scene = scene
        self.camera_path = camera_path
        self.path_coords = np.asarray(path_coords, dtype=float)
        self.progress_path = ProgressPath(self.path_coords)
        self.leader = LeaderMarker(scene=self.scene, path_coords=self.path_coords)

        self.frames = max(2, int(frames))
        self.base_fps = max(1, int(fps or config.FPS))
        self.speed_multiplier = 1.0
        self.frame_index = 0
        self.start_hold_frames = max(
            0,
            int(
                round(
                    float(
                        getattr(
                            config,
                            "START_HOLD_SECONDS",
                            3.0,
                        )
                    )
                    * self.base_fps
                )
            ),
        )
        self.start_hold_index = 0
        self.start_blend_frames = max(
            1,
            int(
                round(
                    float(
                        getattr(
                            config,
                            "START_CAMERA_BLEND_SECONDS",
                            getattr(
                                config,
                                "SLOWDOWN_START_SECONDS",
                                3.0,
                            ),
                        )
                    )
                    * self.base_fps
                )
            ),
        )
        self.paused = False
        self.stopped = False

        self.track_mesh = None
        self.track_actor = None
        self.track_rgba = None
        self.visible_segment_count = -1

        self.track_z_offset = float(getattr(config, "TRACK_Z_OFFSET", 8.0))
        self.track_line_width = float(getattr(config, "TRACK_LINE_WIDTH", 1.5))
        self.track_color = self.hex_to_rgb(str(getattr(config, "TRACK_COLOR", "#FC4C02")))

    @staticmethod
    def hex_to_rgb(value):
        value = value.strip().lstrip("#")
        if len(value) != 6:
            return 252, 76, 2
        try:
            return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
        except ValueError:
            return 252, 76, 2

    def current_progress(self):
        return self.frame_index / max(1, self.frames - 1)

    def toggle_pause(self):
        self.paused = not self.paused
        print("\nPause." if self.paused else "\nReprise.")

    def restart(self):
        self.frame_index = 0
        self.start_hold_index = 0
        self.paused = False
        self.leader.restore_trail(progress=0.0)
        self.update_scene(
            force_track=True,
            start_centered=True,
        )
        print("\nPreview recommencée.")

    def seek_forward(self):
        step = max(1, int(self.frames * 0.05))
        self.frame_index = min(self.frames - 1, self.frame_index + step)
        self.update_scene(force_track=True)
        print(f"\nPosition : {self.current_progress() * 100:.1f} %")

    def seek_backward(self):
        step = max(1, int(self.frames * 0.05))
        self.frame_index = max(0, self.frame_index - step)
        self.update_scene(force_track=True)
        print(f"\nPosition : {self.current_progress() * 100:.1f} %")

    def increase_speed(self):
        self.speed_multiplier = min(4.0, self.speed_multiplier * 1.25)
        print(f"\nVitesse : x{self.speed_multiplier:.2f}")

    def decrease_speed(self):
        self.speed_multiplier = max(0.25, self.speed_multiplier / 1.25)
        print(f"\nVitesse : x{self.speed_multiplier:.2f}")

    def stop(self):
        self.stopped = True
        print("\nFermeture du preview...")

    def create_track_mesh(self):
        if len(self.path_coords) < 2:
            raise ValueError("La trajectoire doit contenir au moins deux points.")

        points = self.path_coords.copy()
        points[:, 2] += self.track_z_offset
        segment_count = len(points) - 1

        lines = np.empty(segment_count * 3, dtype=np.int64)
        lines[0::3] = 2
        lines[1::3] = np.arange(0, segment_count, dtype=np.int64)
        lines[2::3] = np.arange(1, segment_count + 1, dtype=np.int64)

        mesh = pv.PolyData(
            points,
            lines=lines,
        )

        red, green, blue = self.track_color
        rgba = np.zeros((segment_count, 4), dtype=np.uint8)
        rgba[:, 0] = red
        rgba[:, 1] = green
        rgba[:, 2] = blue
        rgba[:, 3] = 0

        mesh.cell_data["track_rgba"] = rgba

        self.track_mesh = mesh
        self.track_rgba = rgba
        self.visible_segment_count = -1

    def create_track_actor(self):
        if self.track_actor is not None:
            return

        self.create_track_mesh()
        self.track_actor = self.scene.add_mesh(
            self.track_mesh,
            scalars="track_rgba",
            rgba=True,
            line_width=self.track_line_width,
            render_lines_as_tubes=False,
            lighting=False,
            preference="cell",
        )

    def segment_count_at_progress(self, progress):
        total_segments = max(0, len(self.path_coords) - 1)

        if not bool(getattr(config, "TRACE_PROGRESSIVE", True)):
            return total_segments

        progress = max(0.0, min(1.0, float(progress)))
        return int(round(progress * total_segments))

    def update_track(self, progress, force=False):
        if self.track_actor is None:
            self.create_track_actor()

        visible_segments = self.segment_count_at_progress(progress)

        if not force and visible_segments == self.visible_segment_count:
            return

        total_segments = len(self.track_rgba)
        visible_segments = max(0, min(total_segments, visible_segments))

        self.track_rgba[:, 3] = 0
        if visible_segments > 0:
            self.track_rgba[:visible_segments, 3] = 255

        self.track_mesh.cell_data["track_rgba"] = self.track_rgba
        self.track_mesh.Modified()

        try:
            self.track_actor.mapper.Update()
        except Exception:
            pass

        self.visible_segment_count = visible_segments

    def start_camera(self):
        position, focal_point, _ = (
            self.camera_path.camera_at_progress(0.0)
        )

        position = np.asarray(position, dtype=float)
        focal_point = np.asarray(focal_point, dtype=float)

        target = self.path_coords[0].copy()
        target[2] += float(
            getattr(
                config,
                "LEADER_Z_OFFSET",
                18.0,
            )
        )

        camera_vector = position - focal_point
        normal_distance = float(np.linalg.norm(camera_vector))

        if normal_distance < 1e-9:
            camera_vector = np.array([0.0, -1.0, 0.35], dtype=float)
            normal_distance = float(np.linalg.norm(camera_vector))

        direction = camera_vector / normal_distance

        zoom_factor = max(
            0.20,
            min(
                1.0,
                float(
                    getattr(
                        config,
                        "START_CAMERA_ZOOM_FACTOR",
                        0.45,
                    )
                ),
            ),
        )

        view_angle = float(
            getattr(
                self.scene.plotter.camera,
                "view_angle",
                30.0,
            )
        )
        leader_radius = float(
            getattr(
                config,
                "LEADER_RADIUS",
                20.0,
            )
        )
        halo_scale = max(
            1.0,
            float(
                getattr(
                    config,
                    "LEADER_HALO_SCALE",
                    1.8,
                )
            ),
        )
        screen_fraction = max(
            0.08,
            min(
                0.30,
                float(
                    getattr(
                        config,
                        "START_LEADER_SCREEN_FRACTION",
                        0.16,
                    )
                ),
            ),
        )

        visible_radius = leader_radius * halo_scale
        allowed_half_angle = np.radians(
            max(
                0.5,
                view_angle * screen_fraction * 0.5,
            )
        )
        minimum_safe_distance = (
            visible_radius
            / max(
                1e-6,
                np.tan(allowed_half_angle),
            )
        )

        start_distance = max(
            normal_distance * zoom_factor,
            minimum_safe_distance,
        )

        return target + direction * start_distance, target

    def set_start_camera(self):
        if not bool(
            getattr(
                config,
                "START_CAMERA_CENTERED",
                True,
            )
        ):
            position, focal_point, _ = (
                self.camera_path.camera_at_progress(0.0)
            )
            self.scene.set_camera(
                position=tuple(position),
                focal_point=tuple(focal_point),
            )
            return

        position, target = self.start_camera()

        self.scene.set_camera(
            position=tuple(position),
            focal_point=tuple(target),
        )

    def finish_camera(self):
        position, focal_point, _ = (
            self.camera_path.camera_at_progress(1.0)
        )
        position = np.asarray(position, dtype=float)
        focal_point = np.asarray(focal_point, dtype=float)

        target = self.path_coords[-1].copy()
        target[2] += float(
            getattr(
                config,
                "LEADER_Z_OFFSET",
                18.0,
            )
        )

        vector = position - focal_point
        distance = float(np.linalg.norm(vector))

        if distance < 1e-9:
            vector = np.array([0.0, -1.0, 0.35], dtype=float)
            distance = float(np.linalg.norm(vector))

        zoom = max(
            0.30,
            min(
                1.50,
                float(
                    getattr(
                        config,
                        "FINISH_CAMERA_ZOOM_FACTOR",
                        0.70,
                    )
                ),
            ),
        )

        return target + vector / distance * distance * zoom, target

    def update_scene(
        self,
        force_track=False,
        start_centered=False,
    ):
        progress = 0.0 if start_centered else self.current_progress()

        if start_centered:
            self.set_start_camera()
        else:
            position, focal_point, _ = (
                self.camera_path.camera_at_progress(progress)
            )
            position = np.asarray(position, dtype=float)
            focal_point = np.asarray(focal_point, dtype=float)

            if self.frame_index < self.start_blend_frames:
                start_position, start_focal = self.start_camera()
                value = (
                    self.frame_index
                    / max(1, self.start_blend_frames)
                )
                value = max(0.0, min(1.0, value))
                blend = value * value * (3.0 - 2.0 * value)

                position = (
                    start_position * (1.0 - blend)
                    + position * blend
                )
                focal_point = (
                    start_focal * (1.0 - blend)
                    + focal_point * blend
                )

            finish_blend_frames = max(
                1,
                int(
                    round(
                        float(
                            getattr(
                                config,
                                "SLOWDOWN_END_SECONDS",
                                3.0,
                            )
                        )
                        * self.base_fps
                    )
                ),
            )
            finish_start = self.frames - finish_blend_frames

            if self.frame_index >= finish_start:
                finish_position, finish_focal = self.finish_camera()
                value = (
                    self.frame_index - finish_start
                ) / max(1, finish_blend_frames)
                value = max(0.0, min(1.0, value))
                blend = value * value * (3.0 - 2.0 * value)

                position = (
                    position * (1.0 - blend)
                    + finish_position * blend
                )
                focal_point = (
                    focal_point * (1.0 - blend)
                    + finish_focal * blend
                )

            self.scene.set_camera(
                position=tuple(position),
                focal_point=tuple(focal_point),
            )

        self.update_track(
            progress=progress,
            force=force_track,
        )

        if bool(getattr(config, "LEADER_ENABLED", False)):
            self.leader.update(progress)

        plotter = self.scene.plotter
        plotter.reset_camera_clipping_range()
        plotter.render()

    def register_controls(self):
        plotter = self.scene.plotter
        plotter.add_key_event("space", self.toggle_pause)
        plotter.add_key_event("r", self.restart)
        plotter.add_key_event("R", self.restart)
        plotter.add_key_event("q", self.stop)
        plotter.add_key_event("Q", self.stop)
        plotter.add_key_event("Right", self.seek_forward)
        plotter.add_key_event("Left", self.seek_backward)
        plotter.add_key_event("plus", self.increase_speed)
        plotter.add_key_event("equal", self.increase_speed)
        plotter.add_key_event("minus", self.decrease_speed)

    def print_header(self):
        print()
        print("===================================")
        print("PREVIEW TRACE OPTIMISÉE")
        print("-----------------------------------")
        print("Caméra      :", getattr(config, "CAMERA_MODE", "flyover"))
        print("Orientation :", getattr(config, "CAMERA_ORIENTATION_MODE", "route"))
        print("Trace       : ligne persistante")
        print("Largeur     :", self.track_line_width, "px")
        print("Décalage Z  :", self.track_z_offset, "m")
        print("-----------------------------------")
        print("Espace        : pause / reprise")
        print("R             : recommencer")
        print("Q             : quitter")
        print("Flèche droite : avancer")
        print("Flèche gauche : reculer")
        print("+ / -         : vitesse")
        print("===================================")
        print()

    def play(self):
        self.print_header()

        plotter = self.scene.plotter
        self.register_controls()
        self.create_track_actor()

        if bool(getattr(config, "LEADER_ENABLED", False)):
            self.leader.create()

        self.update_scene(
            force_track=True,
            start_centered=True,
        )

        plotter.show(
            auto_close=False,
            interactive_update=True,
        )

        last_display = -1

        while not self.stopped:
            frame_start = time.perf_counter()

            try:
                plotter.update()
            except Exception:
                break

            if getattr(plotter, "_closed", False):
                break

            if not self.paused:
                in_start_hold = (
                    self.start_hold_index
                    < self.start_hold_frames
                )

                self.update_scene(
                    start_centered=in_start_hold,
                )

                if in_start_hold:
                    self.start_hold_index += 1
                else:
                    advance = max(
                        1,
                        int(round(self.speed_multiplier)),
                    )
                    self.frame_index += advance

                display_interval = max(1, self.base_fps // 2)

                if (
                    self.frame_index % display_interval == 0
                    and self.frame_index != last_display
                ):
                    print(
                        f"\rPreview : {self.frame_index + 1:4d}/{self.frames} | "
                        f"{self.current_progress() * 100:6.1f} % | "
                        f"x{self.speed_multiplier:.2f}",
                        end="",
                        flush=True,
                    )
                    last_display = self.frame_index

                if self.frame_index >= self.frames:
                    self.frame_index = self.frames - 1
                    self.paused = True
                    self.update_scene(force_track=True)
                    print()
                    print("Fin du preview — R pour recommencer, Q pour quitter.")

            elapsed = time.perf_counter() - frame_start
            remaining = (1.0 / self.base_fps) - elapsed

            if remaining > 0:
                time.sleep(remaining)

        print()
        print("Preview terminé.")
        return
