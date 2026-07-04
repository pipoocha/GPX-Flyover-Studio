import pyvista as pv

from studio.terrain.terrain_grid import TerrainGrid
from studio.terrain.terrain_mesh import TerrainMesh


grid = TerrainGrid.flat(
    width=5000,
    height=5000,
    resolution=50,
)

mesh = TerrainMesh(grid).build()

plotter = pv.Plotter()

plotter.add_mesh(
    mesh,
    color="tan",
    show_edges=True,
)

plotter.show()