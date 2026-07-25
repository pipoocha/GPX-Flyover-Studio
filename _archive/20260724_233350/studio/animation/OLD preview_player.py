import time

import pyvista as pv

import config
from studio.animation.progress_path import ProgressPath
from studio.leader.leader import LeaderMarker
from studio.scene.track import Track


class PreviewPlayer:
    def __init__(
        self,
        scene,
        camera_path,
        path_coords,
        frames=300,
        fps=None,
    ):
        self.scene = scene
        self.camera_path = camera_path

        self.path_coords = path_coords

        self.progress_path = ProgressPath(
            path_coords
        )

        self.leader = LeaderMarker(
            scene=self.scene,
            path_coords=self.path_coords,
        )

        self.frames = max(
            2,
            int(frames),
        )

        self.base_fps = max(
            1,
            int(fps or config.FPS),
        )

        self.frame_index = 0
        self.speed_multiplier = 1.0

        self.paused = False
        self.stopped = False

        self.track_actor = None
        self.last_track_frame = -1

    def current_progress(self):
        return self.frame_index / max(
            1,
            self.frames - 1,
        )

    def toggle_pause(self):
        self.paused = not self.paused

        if self.paused:
            print("\nPause.")
        else:
            print("\nReprise.")

    def restart(self):
        self.frame_index = 0
        self.paused = False
        self.last_track_frame = -1

        self.update_scene(
            force_track=True
        )

        print(
            "\nPreview recommencée."
        )

    def seek_forward(self):
        step = max(
            1,
            int(self.frames * 0.05),
        )

        self.frame_index = min(
            self.frames - 1,
            self.frame_index + step,
        )

        self.last_track_frame = -1

        self.update_scene(
            force_track=True
        )

        print(
            f"\nPosition : "
            f"{self.current_progress() * 100:.1f} %"
        )

    def seek_backward(self):
        step = max(
            1,
            int(self.frames * 0.05),
        )

        self.frame_index = max(
            0,
            self.frame_index - step,
        )

        self.last_track_frame = -1

        self.update_scene(
            force_track=True
        )

        print(
            f"\nPosition : "
            f"{self.current_progress() * 100:.1f} %"
        )

    def increase_speed(self):
        self.speed_multiplier = min(
            4.0,
            self.speed_multiplier * 1.25,
        )

        print(
            f"\nVitesse : "
            f"x{self.speed_multiplier:.2f}"
        )

    def decrease_speed(self):
        self.speed_multiplier = max(
            0.25,
            self.speed_multiplier / 1.25,
        )

        print(
            f"\nVitesse : "
            f"x{self.speed_multiplier:.2f}"
        )

    def stop(self):
        self.stopped = True

        print(
            "\nFermeture du preview..."
        )

    def build_track_mesh(
        self,
        visible_path,
    ):
        render_mode = str(
            getattr(
                config,
                "TRACK_RENDER_MODE",
                "line",
            )
        ).lower()

        if render_mode == "line":
            return pv.lines_from_points(
                visible_path
            )

        return Track(
            visible_path,
            radius=config.TRACK_RADIUS,
            sides=config.TRACK_SIDES,
        ).to_mesh()

    def add_track_actor(
        self,
        visible_path,
    ):
        mesh = self.build_track_mesh(
            visible_path
        )

        render_mode = str(
            getattr(
                config,
                "TRACK_RENDER_MODE",
                "line",
            )
        ).lower()

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
        force=False,
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
            and self.last_track_frame >= 0
            and abs(
                self.frame_index
                - self.last_track_frame
            ) < update_every
        ):
            return

        progress = (
            self.current_progress()
        )

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
            visible_path = (
                self.path_coords
            )

        if len(visible_path) < 2:
            return

        plotter = self.scene.plotter

        if self.track_actor is not None:
            try:
                plotter.remove_actor(
                    self.track_actor,
                    render=False,
                )
            except Exception:
                pass

        self.track_actor = (
            self.add_track_actor(
                visible_path
            )
        )

        self.last_track_frame = (
            self.frame_index
        )

    def update_scene(
        self,
        force_track=False,
    ):
        progress = (
            self.current_progress()
        )

        (
            position,
            focal_point,
            _,
        ) = (
            self.camera_path
            .camera_at_progress(
                progress
            )
        )

        self.scene.set_camera(
            position=tuple(position),
            focal_point=tuple(focal_point),
        )

        self.update_track(
            force=force_track
        )

        self.leader.update(
            progress
        )

        plotter = self.scene.plotter

        plotter.reset_camera_clipping_range()
        plotter.render()

    def register_controls(self):
        plotter = self.scene.plotter

        plotter.add_key_event(
            "space",
            self.toggle_pause,
        )

        plotter.add_key_event(
            "r",
            self.restart,
        )

        plotter.add_key_event(
            "R",
            self.restart,
        )

        plotter.add_key_event(
            "q",
            self.stop,
        )

        plotter.add_key_event(
            "Q",
            self.stop,
        )

        plotter.add_key_event(
            "Right",
            self.seek_forward,
        )

        plotter.add_key_event(
            "Left",
            self.seek_backward,
        )

        plotter.add_key_event(
            "plus",
            self.increase_speed,
        )

        plotter.add_key_event(
            "equal",
            self.increase_speed,
        )

        plotter.add_key_event(
            "minus",
            self.decrease_speed,
        )

    def print_header(self):
        print()
        print("===================================")
        print(
            "PREVIEW DIRECTOR "
            "AVEC LEADER"
        )
        print("-----------------------------------")
        print(
            "Caméra      :",
            getattr(
                config,
                "CAMERA_MODE",
                "flyover",
            ),
        )
        print(
            "Orientation :",
            getattr(
                config,
                "CAMERA_ORIENTATION_MODE",
                "route",
            ),
        )
        print(
            "Preset      :",
            getattr(
                config,
                "CAMERA_PRESET",
                "cinematic",
            ),
        )
        print(
            "Leader      :",
            getattr(
                config,
                "LEADER_STYLE",
                "glow",
            ),
        )
        print("-----------------------------------")
        print(
            "Espace        : pause / reprise"
        )
        print(
            "R             : recommencer"
        )
        print(
            "Q             : quitter"
        )
        print(
            "Flèche droite : avancer"
        )
        print(
            "Flèche gauche : reculer"
        )
        print(
            "+ / -         : vitesse"
        )
        print("===================================")
        print()
        print(
            "Clique une fois dans la "
            "fenêtre 3D avant les touches."
        )
        print()

    def play(self):
        self.print_header()

        plotter = self.scene.plotter

        self.register_controls()

        self.leader.create()

        self.update_scene(
            force_track=True
        )

        plotter.show(
            auto_close=False,
            interactive_update=True,
        )

        last_display = -1

        while not self.stopped:
            frame_start = (
                time.perf_counter()
            )

            try:
                plotter.update()
            except Exception:
                break

            if getattr(
                plotter,
                "_closed",
                False,
            ):
                break

            if not self.paused:
                self.update_scene()

                display_interval = max(
                    1,
                    self.base_fps // 2,
                )

                if (
                    self.frame_index
                    % display_interval == 0
                    and self.frame_index
                    != last_display
                ):
                    print(
                        f"\rPreview : "
                        f"{self.frame_index + 1:4d}/"
                        f"{self.frames} | "
                        f"{self.current_progress() * 100:6.1f} % | "
                        f"x{self.speed_multiplier:.2f}",
                        end="",
                        flush=True,
                    )

                    last_display = (
                        self.frame_index
                    )

                advance = max(
                    1,
                    int(
                        round(
                            self.speed_multiplier
                        )
                    ),
                )

                self.frame_index += advance

                if (
                    self.frame_index
                    >= self.frames
                ):
                    self.frame_index = (
                        self.frames - 1
                    )

                    self.paused = True

                    self.update_scene(
                        force_track=True
                    )

                    print()
                    print(
                        "Fin du preview — "
                        "R pour recommencer, "
                        "Q pour quitter."
                    )

            elapsed = (
                time.perf_counter()
                - frame_start
            )

            target_duration = (
                1.0 / self.base_fps
            )

            remaining = (
                target_duration
                - elapsed
            )

            if remaining > 0:
                time.sleep(
                    remaining
                )

        print()
        print("Preview terminé.")

        return