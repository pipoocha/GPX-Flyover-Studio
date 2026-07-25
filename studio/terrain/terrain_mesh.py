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

        return mesh
