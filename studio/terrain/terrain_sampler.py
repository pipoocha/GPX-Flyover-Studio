import numpy as np


class TerrainSampler:

    def __init__(self, grid):
        self.grid = grid

    def height(self, x, y):

        ix = np.abs(self.grid.x[0] - x).argmin()
        iy = np.abs(self.grid.y[:, 0] - y).argmin()

        return float(self.grid.z[iy, ix])