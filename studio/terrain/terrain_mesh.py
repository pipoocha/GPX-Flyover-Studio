from __future__ import annotations

import numpy as np
import pyvista as pv


WEB_MERCATOR_RADIUS = 6_378_137.0
MAX_MERCATOR_LATITUDE = 85.05112878


class TerrainMesh:
    """Construit la surface du DEM et une jupe latérale optionnelle.

    La surface conserve exactement les altitudes du DEM. La jupe masque les
    bords verticaux du terrain lorsque la caméra descend près de l'horizon.
    """

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
            np.tan(np.pi / 4.0 + latitude_radians / 2.0)
        )

    @property
    def relief(self) -> float:
        return float(np.nanmax(self.grid.z) - np.nanmin(self.grid.z))

    @property
    def horizontal_size(self) -> float:
        width = float(np.nanmax(self.grid.x) - np.nanmin(self.grid.x))
        height = float(np.nanmax(self.grid.y) - np.nanmin(self.grid.y))
        return max(width, height)

    def build(self):
        mesh = pv.StructuredGrid()
        mesh.points = np.c_[
            self.grid.x.ravel(),
            self.grid.y.ravel(),
            self.grid.z.ravel(),
        ]
        mesh.dimensions = (
            self.grid.x.shape[1],
            self.grid.x.shape[0],
            1,
        )

        self.apply_local_texture_coordinates(mesh)

        # Les normales par point donnent un éclairage plus continu sans
        # modifier la géométrie ni les altitudes du DEM.
        try:
            mesh.compute_normals(
                point_normals=True,
                cell_normals=False,
                auto_orient_normals=True,
                consistent_normals=True,
                inplace=True,
            )
        except (AttributeError, TypeError):
            # Compatibilité avec les versions plus anciennes de PyVista/VTK.
            pass

        return mesh

    def build_skirt(self, depth: float | None = None):
        """Crée les parois périphériques sous la surface du terrain."""
        x = np.asarray(self.grid.x, dtype=float)
        y = np.asarray(self.grid.y, dtype=float)
        z = np.asarray(self.grid.z, dtype=float)

        if depth is None:
            depth = max(80.0, min(900.0, self.relief * 0.22))

        base_z = float(np.nanmin(z) - depth)

        borders = [
            (x[0, :], y[0, :], z[0, :]),
            (x[:, -1], y[:, -1], z[:, -1]),
            (x[-1, ::-1], y[-1, ::-1], z[-1, ::-1]),
            (x[::-1, 0], y[::-1, 0], z[::-1, 0]),
        ]

        sections = []
        for border_x, border_y, border_z in borders:
            count = len(border_x)
            if count < 2:
                continue

            top = np.c_[border_x, border_y, border_z]
            bottom = np.c_[
                border_x,
                border_y,
                np.full(count, base_z, dtype=float),
            ]
            points = np.vstack([top, bottom])

            faces = []
            for index in range(count - 1):
                faces.extend(
                    [
                        4,
                        index,
                        index + 1,
                        count + index + 1,
                        count + index,
                    ]
                )

            sections.append(
                pv.PolyData(points, np.asarray(faces, dtype=np.int64))
            )

        if not sections:
            return None

        skirt = sections[0]
        for section in sections[1:]:
            skirt = skirt.merge(section, merge_points=False)

        try:
            skirt.compute_normals(
                point_normals=True,
                cell_normals=False,
                auto_orient_normals=True,
                consistent_normals=True,
                inplace=True,
            )
        except (AttributeError, TypeError):
            pass

        return skirt

    def lighting_parameters(self) -> dict[str, float]:
        """Retourne des valeurs d'éclairage adaptées au relief chargé."""
        size = max(1.0, self.horizontal_size)
        relief_ratio = self.relief / size

        if relief_ratio >= 0.18:
            return {"ambient": 0.43, "diffuse": 0.86, "specular": 0.04}
        if relief_ratio >= 0.08:
            return {"ambient": 0.50, "diffuse": 0.80, "specular": 0.035}
        return {"ambient": 0.57, "diffuse": 0.72, "specular": 0.025}

    def apply_local_texture_coordinates(self, mesh):
        xmin = float(self.grid.x.min())
        xmax = float(self.grid.x.max())
        ymin = float(self.grid.y.min())
        ymax = float(self.grid.y.max())

        width = max(1e-9, xmax - xmin)
        height = max(1e-9, ymax - ymin)

        u = (self.grid.x - xmin) / width
        v = (self.grid.y - ymin) / height

        mesh.active_texture_coordinates = np.c_[u.ravel(), v.ravel()]

    def apply_satellite_texture_coordinates(
        self,
        mesh,
        *,
        metadata,
        projection,
        origin_x,
        origin_y,
    ):
        bounds = metadata.get("geographic_bounds_wgs84", {})

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

        mesh.active_texture_coordinates = np.c_[u.ravel(), v.ravel()]

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
