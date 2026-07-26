import numpy as np
import pyvista as pv


class TerrainMesh:
    def __init__(self, grid):
        self.grid = grid

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

        xmin = self.grid.x.min()
        xmax = self.grid.x.max()
        ymin = self.grid.y.min()
        ymax = self.grid.y.max()

        u = (self.grid.x - xmin) / max(1e-9, xmax - xmin)
        v = (self.grid.y - ymin) / max(1e-9, ymax - ymin)

        texture_coords = np.c_[
            u.ravel(),
            v.ravel(),
        ]

        mesh.active_texture_coordinates = texture_coords

        return mesh