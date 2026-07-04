import pyvista as pv

from studio.scene.scene import Scene
from studio.terrain.terrain_grid import TerrainGrid
from studio.terrain.terrain_mesh import TerrainMesh

grid = TerrainGrid.procedural_mountain(
    width=6000,
    height=6000,
    resolution=60,
)

mesh = TerrainMesh(grid).build()

scene = Scene()

scene.add_mesh(
    mesh,
    cmap="terrain",
    smooth_shading=True,
)

scene.add_light(
    pv.Light(
        position=(3000, -5000, 4500),
        focal_point=(3000, 3000, 0),
        intensity=1.0,
    )
)

scene.add_text(
    "GPX Flyover Studio V3.0.1",
    font_size=18,
)

scene.set_camera(
    position=(3000, -6500, 3500),
    focal_point=(3000, 3000, 300),
)

scene.show()