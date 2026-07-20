import numpy as np
import pyvista as pv

import config
from studio.animation.progress_path import ProgressPath


class LeaderMarker:
    def __init__(
        self,
        scene,
        path_coords,
    ):
        self.scene = scene

        self.path_coords = np.asarray(
            path_coords,
            dtype=float,
        )

        self.progress_path = ProgressPath(
            self.path_coords
        )

        self.enabled = bool(
            getattr(
                config,
                "LEADER_ENABLED",
                True,
            )
        )

        self.style = str(
            getattr(
                config,
                "LEADER_STYLE",
                "glow",
            )
        ).lower()

        self.radius = float(
            getattr(
                config,
                "LEADER_RADIUS",
                20.0,
            )
        )

        self.z_offset = float(
            getattr(
                config,
                "LEADER_Z_OFFSET",
                18.0,
            )
        )

        self.color = str(
            getattr(
                config,
                "LEADER_COLOR",
                "#FC4C02",
            )
        )

        self.halo_scale = float(
            getattr(
                config,
                "LEADER_HALO_SCALE",
                1.8,
            )
        )

        self.halo_opacity = float(
            getattr(
                config,
                "LEADER_HALO_OPACITY",
                0.20,
            )
        )

        # Taille quasiment constante à l'écran.
        self.screen_space_enabled = bool(
            getattr(
                config,
                "LEADER_SCREEN_SPACE_ENABLED",
                True,
            )
        )

        self.reference_distance = float(
            getattr(
                config,
                "LEADER_REFERENCE_DISTANCE",
                3500.0,
            )
        )

        self.minimum_scale = float(
            getattr(
                config,
                "LEADER_MINIMUM_SCALE",
                0.45,
            )
        )

        self.maximum_scale = float(
            getattr(
                config,
                "LEADER_MAXIMUM_SCALE",
                4.0,
            )
        )

        # Traînée lumineuse.
        self.trail_enabled = bool(
            getattr(
                config,
                "LEADER_TRAIL_ENABLED",
                True,
            )
        )

        self.trail_fraction = float(
            getattr(
                config,
                "LEADER_TRAIL_FRACTION",
                0.035,
            )
        )

        self.trail_width = float(
            getattr(
                config,
                "LEADER_TRAIL_WIDTH",
                10.0,
            )
        )

        self.trail_opacity = float(
            getattr(
                config,
                "LEADER_TRAIL_OPACITY",
                0.55,
            )
        )

        self.trail_update_every = max(
            1,
            int(
                getattr(
                    config,
                    "LEADER_TRAIL_UPDATE_EVERY",
                    2,
                )
            ),
        )

        self.core_actor = None
        self.halo_actor = None
        self.trail_actor = None

        self.update_count = 0
        self.current_position = None

    def create(self):
        if not self.enabled:
            return

        if self.core_actor is not None:
            return

        core_mesh = pv.Sphere(
            radius=self.radius,
            theta_resolution=24,
            phi_resolution=24,
        )

        self.core_actor = self.scene.add_mesh(
            core_mesh,
            color=self.color,
            smooth_shading=True,
        )

        if self.style == "glow":
            halo_mesh = pv.Sphere(
                radius=self.radius * self.halo_scale,
                theta_resolution=24,
                phi_resolution=24,
            )

            self.halo_actor = self.scene.add_mesh(
                halo_mesh,
                color=self.color,
                opacity=self.halo_opacity,
                smooth_shading=True,
            )

        self.update(
            progress=0.0,
            force_trail=True,
        )

    def camera_distance_to(self, position):
        try:
            camera_position = np.asarray(
                self.scene.plotter.camera_position[0],
                dtype=float,
            )

            marker_position = np.asarray(
                position,
                dtype=float,
            )

            distance = np.linalg.norm(
                camera_position - marker_position
            )

            return max(
                1.0,
                float(distance),
            )

        except Exception:
            return self.reference_distance

    def screen_scale_at(self, position):
        if not self.screen_space_enabled:
            return 1.0

        distance = self.camera_distance_to(
            position
        )

        scale = (
            distance
            / max(
                1.0,
                self.reference_distance,
            )
        )

        return max(
            self.minimum_scale,
            min(
                self.maximum_scale,
                scale,
            ),
        )

    def update_actor_scale(self, position):
        scale = self.screen_scale_at(
            position
        )

        if self.core_actor is not None:
            self.core_actor.SetScale(
                scale,
                scale,
                scale,
            )

        if self.halo_actor is not None:
            self.halo_actor.SetScale(
                scale,
                scale,
                scale,
            )

    def build_trail_points(self, progress):
        progress = max(
            0.0,
            min(
                1.0,
                float(progress),
            ),
        )

        start_progress = max(
            0.0,
            progress - self.trail_fraction,
        )

        visible_path = (
            self.progress_path.visible_path(
                progress
            )
        )

        if len(visible_path) < 2:
            return None

        _, start_index = (
            self.progress_path.point_at(
                start_progress
            )
        )

        trail_points = visible_path[
            max(
                0,
                start_index - 1,
            ):
        ].copy()

        if len(trail_points) < 2:
            return None

        trail_points[:, 2] += (
            self.z_offset * 0.45
        )

        return trail_points

    def update_trail(
        self,
        progress,
        force=False,
    ):
        if not self.trail_enabled:
            return

        if (
            not force
            and self.update_count
            % self.trail_update_every
            != 0
        ):
            return

        trail_points = (
            self.build_trail_points(
                progress
            )
        )

        if trail_points is None:
            return

        trail_mesh = pv.lines_from_points(
            trail_points
        )

        plotter = self.scene.plotter

        if self.trail_actor is not None:
            try:
                plotter.remove_actor(
                    self.trail_actor,
                    render=False,
                )
            except Exception:
                pass

        self.trail_actor = self.scene.add_mesh(
            trail_mesh,
            color=self.color,
            opacity=self.trail_opacity,
            line_width=self.trail_width,
            render_lines_as_tubes=True,
        )

    def update(
        self,
        progress,
        force_trail=False,
    ):
        if not self.enabled:
            return

        if self.core_actor is None:
            self.create()
            return

        point, _ = (
            self.progress_path.point_at(
                progress
            )
        )

        position = (
            float(point[0]),
            float(point[1]),
            float(
                point[2]
                + self.z_offset
            ),
        )

        self.current_position = position

        self.core_actor.SetPosition(
            position
        )

        if self.halo_actor is not None:
            self.halo_actor.SetPosition(
                position
            )

        self.update_actor_scale(
            position
        )

        self.update_trail(
            progress=progress,
            force=force_trail,
        )

        self.update_count += 1

    def remove(self):
        plotter = self.scene.plotter

        for actor_name in (
            "core_actor",
            "halo_actor",
            "trail_actor",
        ):
            actor = getattr(
                self,
                actor_name,
            )

            if actor is None:
                continue

            try:
                plotter.remove_actor(
                    actor,
                    render=False,
                )
            except Exception:
                pass

            setattr(
                self,
                actor_name,
                None,
            )