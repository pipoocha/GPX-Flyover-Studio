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
        self.progress_path = ProgressPath(path_coords)

        self.enabled = bool(
            getattr(config, "LEADER_ENABLED", True)
        )

        self.radius = float(
            getattr(
                config,
                "LEADER_RADIUS",
                max(18.0, config.TRACK_RADIUS * 3.0),
            )
        )

        self.z_offset = float(
            getattr(
                config,
                "LEADER_Z_OFFSET",
                self.radius * 0.8,
            )
        )

        self.color = getattr(
            config,
            "LEADER_COLOR",
            "#FC4C02",
        )

        self.core_actor = None
        self.halo_actor = None

    def create(self):
        if not self.enabled:
            return

        core_mesh = pv.Sphere(
            radius=self.radius,
            theta_resolution=24,
            phi_resolution=24,
        )

        halo_mesh = pv.Sphere(
            radius=self.radius * 1.75,
            theta_resolution=24,
            phi_resolution=24,
        )

        self.halo_actor = self.scene.add_mesh(
            halo_mesh,
            color=self.color,
            opacity=0.20,
            smooth_shading=True,
        )

        self.core_actor = self.scene.add_mesh(
            core_mesh,
            color=self.color,
            smooth_shading=True,
        )

        self.update(0.0)

    def update(self, progress):
        if not self.enabled:
            return

        if self.core_actor is None:
            self.create()

        point, _ = self.progress_path.point_at(progress)

        position = (
            float(point[0]),
            float(point[1]),
            float(point[2] + self.z_offset),
        )

        self.core_actor.SetPosition(position)
        self.halo_actor.SetPosition(position)

    def remove(self):
        plotter = self.scene.plotter

        if self.core_actor is not None:
            plotter.remove_actor(
                self.core_actor,
                render=False,
            )
            self.core_actor = None

        if self.halo_actor is not None:
            plotter.remove_actor(
                self.halo_actor,
                render=False,
            )
            self.halo_actor = None