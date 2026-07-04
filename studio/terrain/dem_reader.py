import rasterio
import numpy as np

from studio.terrain.terrain_grid import TerrainGrid


class DEMReader:

    def __init__(self, filename):
        self.filename = filename

    def load(self):

        with rasterio.open(self.filename) as src:

            z = src.read(1).astype(float)

            transform = src.transform

            rows, cols = z.shape

            x = np.zeros((rows, cols))
            y = np.zeros((rows, cols))

            for r in range(rows):
                for c in range(cols):
                    xx, yy = rasterio.transform.xy(
                        transform,
                        r,
                        c,
                        offset="center",
                    )

                    x[r, c] = xx
                    y[r, c] = yy

        return TerrainGrid(x, y, z)