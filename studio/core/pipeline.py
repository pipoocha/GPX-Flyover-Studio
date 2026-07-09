import pyvista as pv

import config
from studio.animation.camera_path import CameraPath
from studio.animation.frame_renderer import FrameRenderer
from studio.animation.preview_player import PreviewPlayer
from studio.animation.stage_camera import StageCamera
from studio.director.director_camera import DirectorCamera
from studio.geometry.path_builder import PathBuilder
from studio.io.gpx_loader import GPXLoader
from studio.scene.scene import Scene
from studio.scene.track import Track
from studio.terrain.srtm_grid import SRTMGridBuilder
from studio.terrain.terrain_mesh import TerrainMesh
from studio.terrain.terrain_sampler import TerrainSampler
from studio.video.video_exporter import VideoExporter


class FlyoverPipeline:
    def __init__(self, project):
        self.project = project
        self.origin_x = 0
        self.origin_y = 0

    def load_gpx(self):
        print("Lecture GPX...")
        loader = GPXLoader(self.project.gpx_file)
        self.project.points = loader.load()
        print(f"{len(self.project.points)} points chargés")

    def build_terrain(self):
        print("Création terrain SRTM...")
        builder = SRTMGridBuilder(
            self.project.points,
            resolution=0.0005,
        )

        self.project.grid = builder.build()
        self.project.mesh = TerrainMesh(self.project.grid).build()
        self.project.sampler = TerrainSampler(self.project.grid)

        self.origin_x = builder.origin_x
        self.origin_y = builder.origin_y

    def build_path(self):
        print("Construction trajectoire...")
        self.project.path_coords = PathBuilder(
            self.project.points,
            origin_x=self.origin_x,
            origin_y=self.origin_y,
            sampler=self.project.sampler,
            z_offset=60,
        ).build()

    def build_scene(self, off_screen=True):
        scene = Scene(
            window_size=(config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
            off_screen=off_screen,
        )

        scene.add_mesh(
            self.project.mesh,
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
            f"{config.PROJECT_TITLE} {config.VERSION} - {config.MODE}",
            font_size=18,
        )

        return scene

    def add_full_track(self, scene):
        track = Track(
            self.project.path_coords,
            radius=config.TRACK_RADIUS,
            sides=config.TRACK_SIDES,
        ).to_mesh()

        scene.add_mesh(
            track,
            color="#FC4C02",
            smooth_shading=True,
        )

    def build_camera(self):
        camera_mode = getattr(config, "CAMERA_MODE", "flyover")

        if camera_mode == "director":
            print("Caméra : Director Engine")
            return DirectorCamera(self.project.path_coords)

        if camera_mode == "stage":
            print("Caméra : présentation d'étape")
            return StageCamera(self.project.path_coords)

        print("Caméra : flyover")
        return CameraPath(self.project.path_coords)

    def preview(self):
        scene = self.build_scene(off_screen=False)
        self.add_full_track(scene)

        camera_path = self.build_camera()

        player = PreviewPlayer(
            scene=scene,
            camera_path=camera_path,
            frames=300,
        )

        player.play()

    def render_video(self):
        scene = self.build_scene(off_screen=True)

        camera_path = self.build_camera()

        renderer = FrameRenderer(
            scene=scene,
            camera_path=camera_path,
            path_coords=self.project.path_coords,
            output_dir=config.FRAMES_DIR,
        )

        renderer.render(
            frames=config.TOTAL_FRAMES,
        )

        VideoExporter(
            frames_dir=config.FRAMES_DIR,
            output_file=config.DEFAULT_VIDEO,
            fps=config.FPS,
        ).export()

    def run(self):
        print(f"{config.PROJECT_TITLE} {config.VERSION}")
        print("Mode :", config.MODE)

        self.load_gpx()
        self.build_terrain()
        self.build_path()

        if config.MODE == "PREVIEW":
            self.preview()
            return

        self.render_video()