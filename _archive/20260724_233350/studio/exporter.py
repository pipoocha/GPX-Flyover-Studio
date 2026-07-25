import pyvista as pv

from studio.io.gpx_loader import GPXLoader
from studio.scene.scene import Scene
from studio.scene.track import Track
from studio.terrain.srtm_grid import SRTMGridBuilder
from studio.terrain.terrain_mesh import TerrainMesh


class FlyoverApp:
    def __init__(self, gpx_file):
        self.gpx_file = gpx_file

    def run(self):
        print("Lecture GPX...")
        loader = GPXLoader(self.gpx_file)
        points = loader.load()
        print(f"{len(points)} points chargés")

        print("Création terrain SRTM...")
        builder = SRTMGridBuilder(points, resolution=0.001)
        grid = builder.build()

        mesh = TerrainMesh(grid).build()

        scene = Scene()

        scene.add_mesh(
            mesh,
            cmap="terrain",
            smooth_shading=True,
        )

        track = Track(
            points,
            origin_x=builder.origin_x,
            origin_y=builder.origin_y,
        ).to_mesh()

        scene.add_mesh(
            track,
            color="#FC4C02",
            line_width=6,
            render_lines_as_tubes=True,
        )

        scene.add_light(
            pv.Light(
                position=(3000, -5000, 4500),
                focal_point=(3000, 3000, 0),
                intensity=1.0,
            )
        )

        scene.add_text(
            "GPX Flyover Studio V3.1",
            font_size=18,
        )

        cx = (grid.x.min() + grid.x.max()) / 2
        cy = (grid.y.min() + grid.y.max()) / 2
        cz = (grid.z.min() + grid.z.max()) / 2

        width = grid.x.max() - grid.x.min()
        height = grid.y.max() - grid.y.min()
        size = max(width, height)

        scene.set_camera(
            position=(cx, cy - size * 1.4, cz + size * 0.65),
            focal_point=(cx, cy, cz),
        )

        scene.show()