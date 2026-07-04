import numpy as np

from studio.geometry.resampler import PathResampler
from studio.scene.spline import CatmullRomSpline
from studio.terrain.projection import Projection


class PathBuilder:
    def __init__(self, points, origin_x, origin_y, sampler, z_offset=50):
        self.points = points
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.sampler = sampler
        self.z_offset = z_offset

    def build_raw_coords(self):
        projection = Projection(self.points)

        coords = []
        last = None

        for p in self.points:
            x, y = projection.project_point(p["lat"], p["lon"])
            x -= self.origin_x
            y -= self.origin_y

            z = self.sampler.height(x, y) + self.z_offset

            current = np.array([x, y, z], dtype=float)

            if last is not None:
                if np.linalg.norm(current[:2] - last[:2]) < 0.50:
                    continue

            coords.append(current)
            last = current

        return np.asarray(coords)

    def build(self):

        pts = self.build_raw_coords()

        pts = PathResampler(pts).resample(
            spacing=1.5,
        )

        pts = CatmullRomSpline(
            pts,
            samples_per_segment=8,
        ).interpolate()

        return pts