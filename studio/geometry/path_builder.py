import numpy as np

from studio.geometry.resampler import PathResampler
from studio.scene.spline import CatmullRomSpline


class PathBuilder:
    def __init__(
        self,
        points,
        origin_x,
        origin_y,
        sampler,
        projection,
        z_offset=50,
    ):
        self.points = points
        self.origin_x = float(origin_x)
        self.origin_y = float(origin_y)
        self.sampler = sampler
        self.projection = projection
        self.z_offset = float(z_offset)

    def build_raw_coords(self):
        coords = []
        last = None

        for point in self.points:
            projected_x, projected_y = self.projection.project_point(
                point["lat"],
                point["lon"],
            )

            x = projected_x - self.origin_x
            y = projected_y - self.origin_y
            terrain_z = self.sampler.height(x, y)
            z = terrain_z + self.z_offset

            current = np.array(
                [x, y, z],
                dtype=float,
            )

            if last is not None:
                if np.linalg.norm(current[:2] - last[:2]) < 0.50:
                    continue

            coords.append(current)
            last = current

        if len(coords) < 2:
            raise ValueError(
                "La trajectoire projetée contient moins de deux points."
            )

        return np.asarray(coords, dtype=float)

    def build(self):
        points = self.build_raw_coords()

        points = PathResampler(points).resample(
            spacing=1.5,
        )

        points = CatmullRomSpline(
            points,
            samples_per_segment=8,
        ).interpolate()

        # La spline peut légèrement modifier Z. On recolle chaque point au DEM.
        for index in range(len(points)):
            points[index, 2] = (
                self.sampler.height(
                    points[index, 0],
                    points[index, 1],
                )
                + self.z_offset
            )

        return points
