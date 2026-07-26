from __future__ import annotations

from pathlib import Path

import pyvista as pv

import config
from studio.animation.camera_path import CameraPath
from studio.animation.frame_renderer import FrameRenderer
from studio.animation.preview_player import PreviewPlayer
from studio.animation.stage_camera import StageCamera
from studio.director.director_engine import DirectorEngine
from studio.geometry.path_builder import PathBuilder
from studio.imagery.satellite_texture import SatelliteTexture
from studio.io.gpx_loader import GPXLoader
from studio.scene.scene import Scene
from studio.terrain.copernicus_grid import CopernicusGridBuilder
from studio.terrain.srtm_grid import SRTMGridBuilder
from studio.terrain.terrain_mesh import TerrainMesh
from studio.terrain.terrain_sampler import TerrainSampler
from studio.video.video_exporter import VideoExporter

try:
    from satellite_downloader import create_mosaic
except ImportError:
    create_mosaic = None


class FlyoverPipeline:
    """Pipeline V5 utilisant ProjectConfig comme source principale.

    Les anciens modules utilisent encore ``config``. La méthode
    ``apply_legacy_config`` assure temporairement la compatibilité, sans
    remettre les réglages dans ``config/settings.py``.
    """

    def __init__(self, project):
        self.project = project
        self.origin_x = 0.0
        self.origin_y = 0.0
        self.satellite_texture = None
        self.satellite_metadata = None
        self.terrain_projection = None
        self.terrain_mesh_builder = None
        self.texture_alignment = None

        self.apply_legacy_config()

    def apply_legacy_config(self):
        project = self.project
        video = project.video
        camera = project.camera
        track = project.track
        leader = project.leader
        terrain = project.terrain
        timeline = project.timeline

        config.PROJECT_TITLE = project.title
        config.MODE = video.mode
        config.FPS = int(video.fps)
        config.WINDOW_WIDTH = int(video.width)
        config.WINDOW_HEIGHT = int(video.height)
        config.DEFAULT_VIDEO = Path(video.output)
        effective_travel = timeline.effective_travel
        config.VIDEO_DURATION = int(round(effective_travel))
        config.TOTAL_FRAMES = max(
            2,
            int(round(effective_travel * video.fps)),
        )
        config.PROGRESS_SPEED = float(timeline.speed)

        config.CAMERA_MODE = camera.mode
        config.CAMERA_ORIENTATION_MODE = camera.orientation
        config.LOOK_AHEAD = int(camera.look_ahead)
        config.PREDICTIVE_POSITION_SMOOTHING = float(camera.smoothing)
        config.PREDICTIVE_FOCAL_SMOOTHING = float(camera.smoothing)

        config.CAMERA_LOCAL_FIT_ENABLED = True
        config.CAMERA_LOCAL_FIT_DISTANCE_SCALE = float(camera.distance.scale)
        config.CAMERA_LOCAL_FIT_MIN_DISTANCE = float(camera.distance.minimum)
        config.CAMERA_LOCAL_FIT_MAX_DISTANCE = float(camera.distance.maximum)
        config.CAMERA_LOCAL_FIT_HEIGHT_SCALE = float(camera.height.scale)
        config.CAMERA_LOCAL_FIT_MIN_HEIGHT = float(camera.height.minimum)
        config.CAMERA_LOCAL_FIT_MAX_HEIGHT = float(camera.height.maximum)
        config.CAMERA_LATERAL_DISTANCE_SCALE = float(camera.lateral.scale)
        config.CAMERA_LATERAL_MINIMUM = float(camera.lateral.minimum)
        config.CAMERA_LATERAL_MAXIMUM = float(camera.lateral.maximum)

        config.TRACK_RENDER_MODE = "line"
        config.TRACK_COLOR = track.color
        config.TRACK_LINE_WIDTH = float(track.width)
        config.TRACK_Z_OFFSET = float(track.z_offset)
        config.TRACE_PROGRESSIVE = bool(track.progressive)

        config.LEADER_ENABLED = bool(leader.enabled)
        config.LEADER_STYLE = str(leader.style).lower()
        config.LEADER_COLOR = str(leader.color)
        config.LEADER_RADIUS = float(leader.radius)
        config.LEADER_Z_OFFSET = float(leader.z_offset)
        config.LEADER_HALO_SCALE = float(leader.halo_scale)
        config.LEADER_HALO_OPACITY = float(leader.halo_opacity)
        config.LEADER_TRAIL_ENABLED = bool(leader.trail_enabled)
        config.LEADER_TRAIL_FRACTION = float(leader.trail_fraction)
        config.LEADER_TRAIL_WIDTH = float(leader.trail_width)
        config.LEADER_TRAIL_OPACITY = float(leader.trail_opacity)
        config.LEADER_SCREEN_SPACE_ENABLED = bool(
            leader.screen_space_enabled
        )
        config.LEADER_REFERENCE_DISTANCE = float(
            leader.reference_distance
        )
        config.LEADER_MINIMUM_SCALE = float(
            leader.minimum_scale
        )
        config.LEADER_MAXIMUM_SCALE = float(
            leader.maximum_scale
        )

        config.TERRAIN_SOURCE = terrain.source
        config.USE_SATELLITE = bool(terrain.satellite)
        config.SATELLITE_ZOOM = int(terrain.satellite_zoom)
        config.COPERNICUS_MAX_CELLS = int(terrain.max_cells)
        config.COPERNICUS_MARGIN = float(terrain.margin)

        config.START_HOLD_SECONDS = float(timeline.start_hold)
        config.ARRIVAL_HOLD_SECONDS = float(timeline.arrival_hold)
        config.FLATTEN_TRANSITION_SECONDS = float(timeline.flatten)
        config.PROFILE_ANIMATION_SECONDS = float(timeline.profile_animation)
        config.PROFILE_HOLD_SECONDS = float(timeline.profile_hold)

    def load_gpx(self):
        print("Lecture GPX...")

        loader = GPXLoader(self.project.gpx_file)
        self.project.points = loader.load()

        if len(self.project.points) < 2:
            raise ValueError("Le GPX doit contenir au moins deux points.")

        print(f"{len(self.project.points)} points chargés")

    def build_terrain(self):
        source = self.project.terrain.source.lower()

        if source == "srtm":
            print("Création terrain SRTM...")
            builder = SRTMGridBuilder(
                self.project.points,
                resolution=0.0005,
            )
        elif source == "copernicus":
            print("Création terrain Copernicus GLO-30...")
            builder = CopernicusGridBuilder(
                self.project.points,
                margin=self.project.terrain.margin,
                cache_dir=getattr(
                    config,
                    "COPERNICUS_CACHE_DIR",
                    "cache/dem/copernicus_glo30",
                ),
                max_cells=self.project.terrain.max_cells,
            )
        else:
            raise ValueError(f"Source terrain inconnue : {source}")

        self.project.grid = builder.build()
        self.terrain_projection = builder.projection

        self.terrain_mesh_builder = TerrainMesh(
            self.project.grid
        )
        self.project.mesh = self.terrain_mesh_builder.build()
        self.project.sampler = TerrainSampler(
            self.project.grid
        )

        self.origin_x = float(builder.origin_x)
        self.origin_y = float(builder.origin_y)

    def build_path(self):
        print("Construction trajectoire...")

        self.project.path_coords = PathBuilder(
            self.project.points,
            origin_x=self.origin_x,
            origin_y=self.origin_y,
            sampler=self.project.sampler,
            projection=self.terrain_projection,
            z_offset=self.project.track.z_offset,
        ).build()

    def load_satellite_texture(self):
        if not self.project.terrain.satellite:
            self.satellite_texture = None
            print("Texture satellite désactivée.")
            return

        satellite_cache_dir = Path(
            getattr(
                config,
                "SATELLITE_CACHE_DIR",
                "cache/satellite",
            )
        )

        zoom = int(
            self.project.terrain.satellite_zoom
        )

        satellite = SatelliteTexture(
            gpx_file=self.project.gpx_file,
            cache_dir=satellite_cache_dir,
            zoom=zoom,
            flip_vertical=bool(
                getattr(
                    config,
                    "SATELLITE_FLIP_VERTICAL",
                    True,
                )
            ),
        )

        if not satellite.exists():
            print()
            print(
                "Texture satellite absente : "
                "téléchargement automatique..."
            )

            if create_mosaic is None:
                print(
                    "ATTENTION : satellite_downloader.py "
                    "est introuvable."
                )
                print(
                    "Le preview continue sans texture satellite."
                )
                self.satellite_texture = None
                return

            try:
                create_mosaic(
                    gpx_file=Path(
                        self.project.gpx_file
                    ),
                    zoom=zoom,
                    margin_ratio=float(
                        getattr(
                            config,
                            "SATELLITE_MARGIN_RATIO",
                            0.08,
                        )
                    ),
                    cache_dir=(
                        satellite_cache_dir
                        / "tiles"
                    ),
                    output_dir=satellite_cache_dir,
                )

            except Exception as error:
                print()
                print(
                    "ATTENTION : téléchargement satellite "
                    "impossible."
                )
                print("Détail :", error)
                print(
                    "Le preview continue avec le relief "
                    "sans texture satellite."
                )
                self.satellite_texture = None
                return

            satellite = SatelliteTexture(
                gpx_file=self.project.gpx_file,
                cache_dir=satellite_cache_dir,
                zoom=zoom,
                flip_vertical=bool(
                    getattr(
                        config,
                        "SATELLITE_FLIP_VERTICAL",
                        True,
                    )
                ),
            )

        if not satellite.exists():
            print(
                "ATTENTION : la mosaïque satellite "
                "n'a pas été créée."
            )
            print(
                "Le preview continue sans texture satellite."
            )
            self.satellite_texture = None
            return

        description = satellite.describe()

        print("Texture satellite prête :")
        print("  Image :", description["image"])
        print("  Zoom  :", description["zoom"])

        self.satellite_metadata = satellite.load_metadata()
        self.satellite_texture = satellite.load_texture()

        self.texture_alignment = (
            self.terrain_mesh_builder
            .apply_satellite_texture_coordinates(
                self.project.mesh,
                metadata=self.satellite_metadata,
                projection=self.terrain_projection,
                origin_x=self.origin_x,
                origin_y=self.origin_y,
            )
        )

        print(
            "Texture UV : "
            f"U {self.texture_alignment['u_min']:.3f} à "
            f"{self.texture_alignment['u_max']:.3f} | "
            f"V {self.texture_alignment['v_min']:.3f} à "
            f"{self.texture_alignment['v_max']:.3f}"
        )
        print(
            "Terrain hors mosaïque : "
            f"{self.texture_alignment['outside_percent']:.1f} %"
        )

    def build_scene(self, off_screen=True):
        scene = Scene(
            window_size=(
                self.project.video.width,
                self.project.video.height,
            ),
            off_screen=off_screen,
        )

        if self.satellite_texture is not None:
            scene.add_mesh(
                self.project.mesh,
                texture=self.satellite_texture,
                smooth_shading=True,
                ambient=0.62,
                diffuse=0.72,
                specular=0.03,
            )
        else:
            scene.add_mesh(
                self.project.mesh,
                cmap="terrain",
                smooth_shading=True,
            )

        scene.add_light(
            pv.Light(
                position=(3000, -5000, 7000),
                focal_point=(3000, 3000, 0),
                intensity=0.80,
            )
        )

        scene.add_text(
            f"{self.project.title} {config.VERSION} - {self.project.video.mode}",
            font_size=18,
        )

        return scene

    def build_camera(self):
        mode = self.project.camera.mode.lower()

        if mode == "director":
            print("Caméra : Director cinématographique")
            return DirectorEngine(self.project.path_coords)

        if mode == "stage":
            print("Caméra : présentation d'étape")
            return StageCamera(self.project.path_coords)

        if mode == "flyover":
            print("Caméra : flyover")
            return CameraPath(self.project.path_coords)

        raise ValueError(f"Mode caméra inconnu : {mode}")

    def preview(self):
        scene = self.build_scene(off_screen=False)
        camera_path = self.build_camera()

        frames = max(
            120,
            int(round(self.project.timeline.effective_travel * self.project.video.fps)),
        )

        player = PreviewPlayer(
            scene=scene,
            camera_path=camera_path,
            path_coords=self.project.path_coords,
            frames=frames,
            fps=self.project.video.fps,
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
            frames=max(
                2,
                int(round(
                    self.project.timeline.effective_travel
                    * self.project.video.fps
                )),
            )
        )

        VideoExporter(
            frames_dir=config.FRAMES_DIR,
            output_file=self.project.video.output,
            fps=self.project.video.fps,
        ).export()

    def prepare(self):
        self.load_gpx()
        self.build_terrain()
        self.load_satellite_texture()
        self.build_path()

    def run(self):
        print(f"{self.project.title} {config.VERSION}")
        print("Mode :", self.project.video.mode)

        self.prepare()

        if self.project.video.mode == "PREVIEW":
            self.preview()
            return

        if self.project.video.mode == "VIDEO":
            self.render_video()
            return

        raise ValueError(
            f"Mode vidéo inconnu : {self.project.video.mode}"
        )
