import numpy as np

from studio.terrain.terrain_extent import TerrainExtent
from studio.terrain.srtm_provider import SRTMProvider
from studio.terrain.terrain_grid import TerrainGrid
from studio.terrain.projection import Projection


class SRTMGridBuilder:
    def __init__(self, points, resolution=0.001):
        self.points = points
        self.resolution = resolution
        self.provider = SRTMProvider()
        self.origin_x = 0
        self.origin_y = 0
        self.projection = Projection(self.points)

    def build(self):
        extent = TerrainExtent.from_points(self.points).add_margin(0.02)
        projection = self.projection

        lats = np.arange(extent.south, extent.north + self.resolution, self.resolution)
        lons = np.arange(extent.west, extent.east + self.resolution, self.resolution)

        Lon, Lat = np.meshgrid(lons, lats)

        X = np.zeros_like(Lat, dtype=float)
        Y = np.zeros_like(Lat, dtype=float)
        Z = np.zeros_like(Lat, dtype=float)

        total = Lat.size
        count = 0

        for r in range(Lat.shape[0]):
            for c in range(Lat.shape[1]):
                x, y = projection.project_point(Lat[r, c], Lon[r, c])
                X[r, c] = x
                Y[r, c] = y
                Z[r, c] = self.provider.elevation(Lat[r, c], Lon[r, c])

                count += 1
                if count % 500 == 0:
                    print(f"SRTM {count}/{total}")

        self.origin_x = X.min()
        self.origin_y = Y.min()

        X -= self.origin_x
        Y -= self.origin_y

        return TerrainGrid(X, Y, Z)