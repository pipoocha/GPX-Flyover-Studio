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

        self.progress_path = ProgressPath(
            path_coords
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

        self.core_actor = None
        self.halo_actor = None

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
                radius=(
                    self.radius
                    * self.halo_scale
                ),
                theta_resolution=24,
                phi_resolution=24,
            )

            self.halo_actor = (
                self.scene.add_mesh(
                    halo_mesh,
                    color=self.color,
                    opacity=self.halo_opacity,
                    smooth_shading=True,
                )
            )

        self.update(0.0)

    def update(self, progress):
        if not self.enabled:
            return

        if self.core_actor is None:
            self.create()

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

        if self.core_actor is not None:
            self.core_actor.SetPosition(
                position
            )

        if self.halo_actor is not None:
            self.halo_actor.SetPosition(
                position
            )

    def remove(self):
        plotter = self.scene.plotter

        if self.core_actor is not None:
            try:
                plotter.remove_actor(
                    self.core_actor,
                    render=False,
                )
            except Exception:
                pass

            self.core_actor = None

        if self.halo_actor is not None:
            try:
                plotter.remove_actor(
                    self.halo_actor,
                    render=False,
                )
            except Exception:
                pass

            self.halo_actor = None