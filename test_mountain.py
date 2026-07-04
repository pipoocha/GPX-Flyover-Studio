import pyvista as pv

from studio.terrain.terrain_grid import TerrainGrid
from studio.terrain.terrain_mesh import TerrainMesh


grid = TerrainGrid.procedural_mountain(
    width=6000,
    height=6000,
    resolution=60,
)

mesh = TerrainMesh(grid).build()

plotter = pv.Plotter(window_size=(1400, 900))
plotter.set_background("black")

plotter.add_mesh(
    mesh,
    cmap="terrain",
    show_edges=False,
    smooth_shading=True,
)

plotter.add_light(
    pv.Light(
        position=(3000, -4000, 5000),
        focal_point=(3000, 3000, 0),
        color="white",
        intensity=0.9,
    )
)

plotter.add_text("Terrain procedural - GPX Flyover Studio V3", font_size=14)
plotter.camera_position = [
    (3000, -6500, 3500),
    (3000, 3000, 400),
    (0, 0, 1),
]

plotter.show()