from __future__ import annotations

import math

import numpy as np
import pyvista as pv


WEB_MERCATOR_RADIUS = 6_378_137.0
MAX_MERCATOR_LATITUDE = 85.05112878


class TerrainMesh:
    def __init__(self, grid):
        self.grid = grid

    @staticmethod
    def _mercator_x(longitude):
        return WEB_MERCATOR_RADIUS * np.radians(longitude)

    @staticmethod
    def _mercator_y(latitude):
        latitude = np.clip(
            latitude,
            -MAX_MERCATOR_LATITUDE,
            MAX_MERCATOR_LATITUDE,
        )

        latitude_radians = np.radians(latitude)

        return WEB_MERCATOR_RADIUS * np.log(
            np.tan(
                np.pi / 4.0
                + latitude_radians / 2.0
            )
        )

    def build(self):
        mesh = pv.StructuredGrid()

        points = np.c_[
            self.grid.x.ravel(),
            self.grid.y.ravel(),
            self.grid.z.ravel(),
        ]

        mesh.points = points

        mesh.dimensions = (
            self.grid.x.shape[1],
            self.grid.x.shape[0],
            1,
        )

        self.apply_local_texture_coordinates(mesh)

        return mesh

    def apply_local_texture_coordinates(self, mesh):
        xmin = float(self.grid.x.min())
        xmax = float(self.grid.x.max())
        ymin = float(self.grid.y.min())
        ymax = float(self.grid.y.max())

        width = max(1e-9, xmax - xmin)
        height = max(1e-9, ymax - ymin)

        u = (self.grid.x - xmin) / width
        v = (self.grid.y - ymin) / height

        mesh.active_texture_coordinates = np.c_[
            u.ravel(),
            v.ravel(),
        ]

    def apply_satellite_texture_coordinates(
        self,
        mesh,
        *,
        metadata,
        projection,
        origin_x,
        origin_y,
    ):
        bounds = metadata.get(
            "geographic_bounds_wgs84",
            {},
        )

        west = bounds.get("west")
        south = bounds.get("south")
        east = bounds.get("east")
        north = bounds.get("north")

        if None in (west, south, east, north):
            raise ValueError(
                "Les métadonnées satellite ne contiennent pas "
                "geographic_bounds_wgs84 complet."
            )

        absolute_x = self.grid.x + float(origin_x)
        absolute_y = self.grid.y + float(origin_y)

        latitudes, longitudes = projection.unproject_arrays(
            absolute_x,
            absolute_y,
        )

        mercator_x = self._mercator_x(longitudes)
        mercator_y = self._mercator_y(latitudes)

        west_x = float(self._mercator_x(float(west)))
        east_x = float(self._mercator_x(float(east)))
        south_y = float(self._mercator_y(float(south)))
        north_y = float(self._mercator_y(float(north)))

        width = max(1e-9, east_x - west_x)
        height = max(1e-9, north_y - south_y)

        u = (mercator_x - west_x) / width
        v = (mercator_y - south_y) / height

        mesh.active_texture_coordinates = np.c_[
            u.ravel(),
            v.ravel(),
        ]

        return {
            "u_min": float(np.min(u)),
            "u_max": float(np.max(u)),
            "v_min": float(np.min(v)),
            "v_max": float(np.max(v)),
            "outside_percent": float(
                100.0
                * np.mean(
                    (u < 0.0)
                    | (u > 1.0)
                    | (v < 0.0)
                    | (v > 1.0)
                )
            ),
        }
