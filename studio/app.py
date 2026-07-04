import pyvista as pv

import config
from studio.animation.camera_path import CameraPath
from studio.animation.frame_renderer import FrameRenderer
from studio.geometry.path_builder import PathBuilder
from studio.io.gpx_loader import GPXLoader
from studio.scene.scene import Scene
from studio.terrain.srtm_grid import SRTMGridBuilder
from studio.terrain.terrain_mesh import TerrainMesh
from studio.terrain.terrain_sampler import TerrainSampler
from studio.video.video_exporter import VideoExporter


class FlyoverApp:
    def __init__(self, gpx_file):
        self.gpx_file = gpx_file

    def run(self):
        print(f"{config.PROJECT_TITLE} {config.VERSION}")
        print("Lecture GPX...")

        loader = GPXLoader(self.gpx_file)
        points = loader.load()
        print(f"{len(points)} points chargés")

        print("Création terrain SRTM...")
        builder = SRTMGridBuilder(points, resolution=0.0005)
        grid = builder.build()

        mesh = TerrainMesh(grid).build()

        scene = Scene(
            window_size=(config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
            off_screen=True,
        )

        scene.add_mesh(
            mesh,
            cmap="terrain",
            smooth_shading=True,
        )

        sampler = TerrainSampler(grid)

        print("Construction trajectoire...")
        path_coords = PathBuilder(
            points,
            origin_x=builder.origin_x,
            origin_y=builder.origin_y,
            sampler=sampler,
            z_offset=60,
        ).build()

        scene.add_light(
            pv.Light(
                position=(3000, -5000, 4500),
                focal_point=(3000, 3000, 0),
                intensity=1.0,
            )
        )

        scene.add_text(
            f"{config.PROJECT_TITLE} {config.VERSION} - {config.MODE}",
            font_size=18,
        )

        camera_path = CameraPath(path_coords)

        renderer = FrameRenderer(
            scene=scene,
            camera_path=camera_path,
            path_coords=path_coords,
            output_dir=config.FRAMES_DIR,
        )

        renderer.render(frames=config.TOTAL_FRAMES)

        VideoExporter(
            frames_dir=config.FRAMES_DIR,
            output_file=config.DEFAULT_VIDEO,
            fps=config.FPS,
        ).export()