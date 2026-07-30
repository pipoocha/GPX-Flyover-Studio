from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont

import config
from studio.animation.progress_path import ProgressPath
from studio.leader.leader import LeaderMarker
from studio.timeline.timeline import TimelineMapper


class FrameRenderer:
    """
    Rendu vidéo V15.

    Séquence :
    - pause au départ, avec le début de la trace visible ;
    - parcours avec ralentissement progressif au départ et à l'arrivée ;
    - pause sur l'arrivée ;
    - transition vers une vue verticale du parcours complet ;
    - profil altimétrique animé dans un coin ;
    - maintien final réglable du profil.
    """

    def __init__(self, scene, camera_path, path_coords, output_dir=None):
        self.scene = scene
        self.camera_path = camera_path
        self.path_coords = np.asarray(path_coords, dtype=float)
        self.progress_path = ProgressPath(self.path_coords)
        self.output_dir = Path(output_dir or config.FRAMES_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.track_mesh = None
        self.track_actor = None
        self.track_rgba = None
        self.visible_segment_count = -1

        self.track_z_offset = float(getattr(config, "TRACK_Z_OFFSET", 8.0))
        self.track_line_width = float(getattr(config, "TRACK_LINE_WIDTH", 1.5))
        self.track_color_hex = str(getattr(config, "TRACK_COLOR", "#FC4C02"))
        self.track_color = self.hex_to_rgb(self.track_color_hex)
        self.start_visible_segments = max(
            1,
            int(getattr(config, "START_VISIBLE_SEGMENTS", 12)),
        )

        self.leader = LeaderMarker(scene=self.scene, path_coords=self.path_coords)

        self.profile_distances = self.compute_profile_distances(self.path_coords)
        self.profile_elevations = self.path_coords[:, 2].astype(float)
        self.profile_stats = self.compute_profile_stats(
            self.profile_distances,
            self.profile_elevations,
        )
        effective_travel = float(
            getattr(
                config,
                "VIDEO_DURATION",
                30.0,
            )
        )

        self.timeline_mapper = TimelineMapper(
            type(
                "TimelineProxy",
                (),
                {
                    "travel": effective_travel,
                    "effective_travel": effective_travel,
                    "slowdown_start": float(
                        getattr(
                            config,
                            "SLOWDOWN_START_SECONDS",
                            2.0,
                        )
                    ),
                    "slowdown_end": float(
                        getattr(
                            config,
                            "SLOWDOWN_END_SECONDS",
                            3.0,
                        )
                    ),
                },
            )()
        )
        self.profile_marker_actor = None

    @staticmethod
    def hex_to_rgb(value):
        value = value.strip().lstrip("#")
        if len(value) != 6:
            return 252, 76, 2
        try:
            return (
                int(value[0:2], 16),
                int(value[2:4], 16),
                int(value[4:6], 16),
            )
        except ValueError:
            return 252, 76, 2

    @staticmethod
    def smoothstep(value):
        value = max(0.0, min(1.0, float(value)))
        return value * value * (3.0 - 2.0 * value)

    @staticmethod
    def smootherstep(value):
        value = max(0.0, min(1.0, float(value)))
        return value * value * value * (
            value * (value * 6.0 - 15.0) + 10.0
        )

    def eased_progress(self, value):
        return self.timeline_mapper.travel_progress(value)

    def clear_frames(self):
        for file in self.output_dir.glob("frame_*.png"):
            file.unlink()

    def create_track_actor(self):
        points = self.path_coords.copy()
        points[:, 2] += self.track_z_offset

        segment_count = len(points) - 1
        lines = np.empty(segment_count * 3, dtype=np.int64)
        lines[0::3] = 2
        lines[1::3] = np.arange(0, segment_count, dtype=np.int64)
        lines[2::3] = np.arange(1, segment_count + 1, dtype=np.int64)

        mesh = pv.PolyData(points, lines=lines)

        red, green, blue = self.track_color
        rgba = np.zeros((segment_count, 4), dtype=np.uint8)
        rgba[:, 0] = red
        rgba[:, 1] = green
        rgba[:, 2] = blue
        rgba[:, 3] = 0
        mesh.cell_data["track_rgba"] = rgba

        self.track_mesh = mesh
        self.track_rgba = rgba
        self.track_actor = self.scene.add_mesh(
            mesh,
            scalars="track_rgba",
            rgba=True,
            preference="cell",
            line_width=self.track_line_width,
            render_lines_as_tubes=False,
            lighting=False,
        )

    def update_track(self, progress, force=False, minimum_segments=0):
        total_segments = len(self.track_rgba)

        if bool(getattr(config, "TRACE_PROGRESSIVE", True)):
            visible_segments = int(
                round(max(0.0, min(1.0, float(progress))) * total_segments)
            )
        else:
            visible_segments = total_segments

        visible_segments = max(visible_segments, int(minimum_segments))
        visible_segments = min(total_segments, visible_segments)

        if not force and visible_segments == self.visible_segment_count:
            return

        self.track_rgba[:, 3] = 0
        if visible_segments > 0:
            self.track_rgba[:visible_segments, 3] = 255

        self.track_mesh.cell_data["track_rgba"] = self.track_rgba
        self.track_mesh.Modified()
        self.visible_segment_count = visible_segments

    def frame_path(self, frame_index):
        return self.output_dir / f"frame_{frame_index:05d}.png"

    def save_frame(self, frame_index):
        self.scene.plotter.screenshot(str(self.frame_path(frame_index)))

    def start_camera(self):
        """Cadrage très serré du départ, centré et sans couper le leader."""
        position, focal_point, _ = self.camera_path.camera_at_progress(0.0)

        position = np.asarray(position, dtype=float)
        focal_point = np.asarray(focal_point, dtype=float)

        target = self.path_coords[0].copy()
        target[2] += float(
            getattr(
                config,
                "LEADER_Z_OFFSET",
                18.0,
            )
        )

        camera_vector = position - focal_point
        normal_distance = float(np.linalg.norm(camera_vector))

        if normal_distance < 1e-9:
            camera_vector = np.array([0.0, -1.0, 0.35], dtype=float)
            normal_distance = float(np.linalg.norm(camera_vector))

        direction = camera_vector / normal_distance

        zoom_factor = max(
            0.20,
            min(
                1.0,
                float(
                    getattr(
                        config,
                        "START_CAMERA_ZOOM_FACTOR",
                        0.45,
                    )
                ),
            ),
        )

        view_angle = float(
            getattr(
                self.scene.plotter.camera,
                "view_angle",
                30.0,
            )
        )

        leader_radius = float(
            getattr(
                config,
                "LEADER_RADIUS",
                20.0,
            )
        )
        halo_scale = max(
            1.0,
            float(
                getattr(
                    config,
                    "LEADER_HALO_SCALE",
                    1.8,
                )
            ),
        )
        screen_fraction = max(
            0.08,
            min(
                0.30,
                float(
                    getattr(
                        config,
                        "START_LEADER_SCREEN_FRACTION",
                        0.16,
                    )
                ),
            ),
        )

        visible_radius = leader_radius * halo_scale
        allowed_half_angle = np.radians(
            max(
                0.5,
                view_angle * screen_fraction * 0.5,
            )
        )
        minimum_safe_distance = (
            visible_radius
            / max(
                1e-6,
                np.tan(allowed_half_angle),
            )
        )

        start_distance = max(
            normal_distance * zoom_factor,
            minimum_safe_distance,
        )

        centered_position = (
            target
            + direction * start_distance
        )

        return centered_position, target

    def set_start_camera(self):
        if not bool(
            getattr(
                config,
                "START_CAMERA_CENTERED",
                True,
            )
        ):
            return self.set_route_camera(0.0)

        position, focal_point = self.start_camera()

        self.scene.set_camera(
            position=tuple(position),
            focal_point=tuple(focal_point),
        )

        return position, focal_point

    def set_route_camera(self, progress):
        position, focal_point, _ = self.camera_path.camera_at_progress(progress)
        self.scene.set_camera(
            position=tuple(position),
            focal_point=tuple(focal_point),
        )
        return np.asarray(position, dtype=float), np.asarray(focal_point, dtype=float)

    def finish_camera(self):
        route_position, route_focal, _ = (
            self.camera_path.camera_at_progress(1.0)
        )
        route_position = np.asarray(route_position, dtype=float)
        route_focal = np.asarray(route_focal, dtype=float)

        target = self.path_coords[-1].copy()
        target[2] += float(
            getattr(
                config,
                "LEADER_Z_OFFSET",
                18.0,
            )
        )

        vector = route_position - route_focal
        distance = float(np.linalg.norm(vector))

        if distance < 1e-9:
            vector = np.array([0.0, -1.0, 0.35], dtype=float)
            distance = float(np.linalg.norm(vector))

        direction = vector / distance
        zoom = max(
            0.30,
            min(
                1.50,
                float(
                    getattr(
                        config,
                        "FINISH_CAMERA_ZOOM_FACTOR",
                        0.70,
                    )
                ),
            ),
        )

        return target + direction * distance * zoom, target

    def set_finish_camera(self):
        position, focal = self.finish_camera()
        self.scene.set_camera(
            position=tuple(position),
            focal_point=tuple(focal),
        )

    def render_start_frame(
        self,
        frame_index,
        force_track=False,
    ):
        """Image de départ fixe : leader centré et progression strictement nulle."""
        self.set_start_camera()

        self.update_track(
            0.0,
            force=force_track,
            minimum_segments=self.start_visible_segments,
        )

        if bool(getattr(config, "LEADER_ENABLED", False)):
            self.leader.update(0.0)

        plotter = self.scene.plotter
        plotter.reset_camera_clipping_range()
        plotter.render()
        plotter.update()
        self.save_frame(frame_index)

    def active_poi(self, progress):
        total_km=max(.001,float(self.profile_stats["distance_km"])); travel=max(.1,float(getattr(config,"VIDEO_DURATION",30.0)))
        for poi in list(getattr(config,"POIS",[])):
            target=max(0.0,min(1.0,float(poi.get("kilometer",0.0))/total_km)); half=max(.5,float(poi.get("duration",2.5)))/travel/2.0
            if abs(float(progress)-target)<=half: return poi
        return None

    @staticmethod
    def _poi_rgb(value):
        value=str(value).strip().lstrip("#")
        try: return tuple(int(value[i:i+2],16) for i in (0,2,4)) if len(value)==6 else (255,255,255)
        except ValueError: return 255,255,255

    def draw_poi_flash(self, image, poi):
        image=image.convert("RGB"); draw=ImageDraw.Draw(image,"RGBA"); w,h=image.size; pw=min(int(w*.44),620); ph=min(int(h*.20),170); m=max(18,int(w*.02)); left=w-pw-m; top=m; right=w-m; bottom=top+ph; r,g,b=self._poi_rgb(poi.get("color","#FFFFFF")); font=ImageFont.load_default()
        draw.rounded_rectangle((left,top,right,bottom),radius=18,fill=(8,8,8,225),outline=(r,g,b,240),width=4)
        draw.text((left+18,top+16),str(poi.get("name","POI")),fill=(255,255,255,255),font=font)
        draw.text((left+18,top+48),f"{poi.get('type','Libre')}  |  km {float(poi.get('kilometer',0.0)):.1f}",fill=(r,g,b,255),font=font)
        note=str(poi.get("text","")).strip()
        if note: draw.text((left+18,top+80),note[:90],fill=(235,235,235,235),font=font)
        return image

    def render_route_frame(
        self,
        frame_index,
        progress,
        force_track=False,
        minimum_segments=0,
        trail_fade_progress=None,
        start_camera_blend=None,
        finish_camera_blend=None,
    ):
        if finish_camera_blend is not None:
            route_position, route_focal, _ = (
                self.camera_path.camera_at_progress(progress)
            )
            route_position = np.asarray(route_position, dtype=float)
            route_focal = np.asarray(route_focal, dtype=float)
            finish_position, finish_focal = self.finish_camera()
            blend = self.smootherstep(finish_camera_blend)

            position = (
                route_position * (1.0 - blend)
                + finish_position * blend
            )
            focal = (
                route_focal * (1.0 - blend)
                + finish_focal * blend
            )

            self.scene.set_camera(
                position=tuple(position),
                focal_point=tuple(focal),
            )
        elif start_camera_blend is None:
            self.set_route_camera(progress)
        else:
            route_position, route_focal, _ = (
                self.camera_path.camera_at_progress(progress)
            )
            route_position = np.asarray(route_position, dtype=float)
            route_focal = np.asarray(route_focal, dtype=float)

            start_position, start_focal = self.start_camera()
            blend = self.smootherstep(start_camera_blend)

            position = (
                start_position * (1.0 - blend)
                + route_position * blend
            )
            focal = (
                start_focal * (1.0 - blend)
                + route_focal * blend
            )

            self.scene.set_camera(
                position=tuple(position),
                focal_point=tuple(focal),
            )
        self.update_track(
            progress,
            force=force_track,
            minimum_segments=minimum_segments,
        )

        if bool(getattr(config, "LEADER_ENABLED", False)):
            self.leader.update(progress)

            if trail_fade_progress is not None:
                self.leader.set_trail_fade(
                    trail_fade_progress
                )

        plotter = self.scene.plotter
        plotter.reset_camera_clipping_range()
        plotter.render()
        plotter.update()
        self.save_frame(frame_index)
        poi = self.active_poi(progress)
        if poi is not None:
            output_file = self.frame_path(frame_index)
            with Image.open(output_file) as image:
                self.draw_poi_flash(image, poi).save(output_file)

    def create_profile_marker(self):
        """Point mobile sur la trace, synchronisé avec le profil."""
        if self.profile_marker_actor is not None:
            return

        leader_radius = float(
            getattr(
                config,
                "LEADER_RADIUS",
                20.0,
            )
        )
        radius = max(
            16.0,
            float(
                getattr(
                    config,
                    "PROFILE_MAP_MARKER_RADIUS",
                    leader_radius * 1.4,
                )
            ),
        )

        marker = pv.Sphere(
            radius=radius,
            theta_resolution=28,
            phi_resolution=28,
        )

        marker_color = str(
            getattr(
                config,
                "LEADER_COLOR",
                self.track_color_hex,
            )
        )

        self.profile_marker_actor = self.scene.add_mesh(
            marker,
            color=marker_color,
            smooth_shading=True,
            lighting=False,
        )

    def profile_marker_position(self, progress):
        """Interpolation selon la distance réelle, pas selon l'index GPX."""
        progress = max(
            0.0,
            min(1.0, float(progress)),
        )

        target_distance = (
            progress
            * float(self.profile_distances[-1])
        )

        upper_index = int(
            np.searchsorted(
                self.profile_distances,
                target_distance,
                side="left",
            )
        )
        upper_index = max(
            1,
            min(
                len(self.path_coords) - 1,
                upper_index,
            ),
        )
        lower_index = upper_index - 1

        lower_distance = float(
            self.profile_distances[lower_index]
        )
        upper_distance = float(
            self.profile_distances[upper_index]
        )
        span = max(
            1e-9,
            upper_distance - lower_distance,
        )
        local_progress = (
            target_distance - lower_distance
        ) / span

        point = (
            self.path_coords[lower_index]
            * (1.0 - local_progress)
            + self.path_coords[upper_index]
            * local_progress
        )

        point = point.copy()
        point[2] += self.track_z_offset + 25.0
        return point

    def update_profile_marker(self, progress):
        self.create_profile_marker()

        point = self.profile_marker_position(
            progress
        )
        self.profile_marker_actor.SetPosition(
            tuple(point)
        )

        try:
            self.profile_marker_actor.SetVisibility(True)
        except Exception:
            pass

    def top_down_camera(self):
        """
        Cadre toute la trace dans la zone supérieure de l'image.

        La bande inférieure est réservée au profil altimétrique.
        Le calcul utilise le FOV réel et le format de la vidéo.
        """
        xy = self.path_coords[:, :2]

        minimum = xy.min(axis=0)
        maximum = xy.max(axis=0)
        route_center = (minimum + maximum) / 2.0
        center_z = float(
            np.mean(self.path_coords[:, 2])
        )

        route_width = max(
            1.0,
            float(maximum[0] - minimum[0]),
        )
        route_height = max(
            1.0,
            float(maximum[1] - minimum[1]),
        )

        image_width = max(
            1.0,
            float(
                getattr(
                    config,
                    "WINDOW_WIDTH",
                    1280,
                )
            ),
        )
        image_height = max(
            1.0,
            float(
                getattr(
                    config,
                    "WINDOW_HEIGHT",
                    720,
                )
            ),
        )
        aspect_ratio = image_width / image_height

        # 30 % de la hauteur est réservée au profil.
        profile_band_ratio = max(
            0.20,
            min(
                0.40,
                float(
                    getattr(
                        config,
                        "FINAL_PROFILE_BAND_RATIO",
                        0.30,
                    )
                ),
            ),
        )
        map_height_ratio = 1.0 - profile_band_ratio

        # Marge généreuse pour que la trace ne touche jamais le bord.
        route_padding = max(
            1.10,
            float(
                getattr(
                    config,
                    "FINAL_ROUTE_PADDING",
                    1.30,
                )
            ),
        )

        vertical_fov = np.radians(
            max(
                10.0,
                float(
                    getattr(
                        self.scene.plotter.camera,
                        "view_angle",
                        30.0,
                    )
                ),
            )
        )
        horizontal_fov = 2.0 * np.arctan(
            np.tan(vertical_fov / 2.0)
            * aspect_ratio
        )

        distance_for_width = (
            route_width
            * route_padding
            / max(
                1e-6,
                2.0 * np.tan(horizontal_fov / 2.0),
            )
        )

        # La hauteur disponible pour la carte est réduite par la bande profil.
        distance_for_height = (
            route_height
            * route_padding
            / max(
                1e-6,
                2.0
                * np.tan(vertical_fov / 2.0)
                * map_height_ratio,
            )
        )

        camera_distance = max(
            float(
                getattr(
                    config,
                    "FINAL_TOPDOWN_MIN_HEIGHT",
                    2500.0,
                )
            ),
            distance_for_width,
            distance_for_height,
        )

        # Décalage du parcours vers le haut de l'image.
        full_visible_height = (
            2.0
            * camera_distance
            * np.tan(vertical_fov / 2.0)
        )
        upward_shift = (
            full_visible_height
            * profile_band_ratio
            * 0.52
        )

        focal = np.array(
            [
                route_center[0],
                route_center[1] - upward_shift,
                center_z,
            ],
            dtype=float,
        )

        position = np.array(
            [
                focal[0],
                focal[1],
                float(self.path_coords[:, 2].max())
                + camera_distance,
            ],
            dtype=float,
        )

        # Le nord reste en haut de l'image.
        view_up = (0.0, 1.0, 0.0)
        return position, focal, view_up

    def set_explicit_camera(self, position, focal, view_up):
        self.scene.plotter.camera_position = [
            tuple(position),
            tuple(focal),
            tuple(view_up),
        ]

    def render_flatten_transition(
        self,
        frame_index,
        transition_progress,
        start_position,
        start_focal,
    ):
        if self.profile_marker_actor is not None:
            try:
                self.profile_marker_actor.SetVisibility(False)
            except Exception:
                pass
        target_position, target_focal, target_up = self.top_down_camera()
        blend = self.smootherstep(transition_progress)

        position = start_position * (1.0 - blend) + target_position * blend
        focal = start_focal * (1.0 - blend) + target_focal * blend

        start_up = np.array([0.0, 0.0, 1.0], dtype=float)
        end_up = np.asarray(target_up, dtype=float)
        view_up = start_up * (1.0 - blend) + end_up * blend
        norm = np.linalg.norm(view_up)
        if norm < 1e-9:
            view_up = end_up
        else:
            view_up /= norm

        self.set_explicit_camera(position, focal, view_up)
        self.update_track(1.0, force=True)

        terrain_actor = getattr(self.scene, "terrain_actor", None)
        if terrain_actor is not None:
            mean_z = float(getattr(self.scene, "terrain_mean_z", 0.0))
            vertical_scale = 1.0 - 0.94 * blend
            try:
                terrain_actor.SetOrigin(0.0, 0.0, mean_z)
                terrain_actor.SetScale(1.0, 1.0, vertical_scale)
            except Exception:
                pass

        plotter = self.scene.plotter
        plotter.reset_camera_clipping_range()
        plotter.render()
        plotter.update()
        self.save_frame(frame_index)

    @staticmethod
    def compute_profile_distances(path_coords):
        differences = np.diff(path_coords[:, :3], axis=0)
        lengths = np.linalg.norm(differences, axis=1)
        return np.insert(np.cumsum(lengths), 0, 0.0)

    @staticmethod
    def compute_profile_stats(distances, elevations):
        changes = np.diff(elevations)
        return {
            "distance_km": float(distances[-1] / 1000.0),
            "gain": float(changes[changes > 0].sum()),
            "loss": float(-changes[changes < 0].sum()),
            "minimum": float(elevations.min()),
            "maximum": float(elevations.max()),
        }

    def profile_rectangle(self, image_width, image_height):
        """
        Le profil occupe une bande dédiée sous la carte.

        Il ne flotte plus sur la trace et ne peut donc plus la masquer.
        """
        margin = max(
            10,
            int(
                getattr(
                    config,
                    "PROFILE_INSET_MARGIN",
                    16,
                )
            ),
        )
        band_ratio = max(
            0.20,
            min(
                0.40,
                float(
                    getattr(
                        config,
                        "FINAL_PROFILE_BAND_RATIO",
                        0.30,
                    )
                ),
            ),
        )

        band_height = max(
            150,
            int(image_height * band_ratio),
        )

        left = margin
        right = image_width - margin
        bottom = image_height - margin
        top = max(
            margin,
            bottom - band_height + margin,
        )

        return left, top, right, bottom

    def draw_profile_inset(self, image, progress):
        image = image.convert("RGB")
        draw = ImageDraw.Draw(image, "RGBA")
        width, height = image.size
        left, top, right, bottom = self.profile_rectangle(width, height)

        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=16,
            fill=(10, 10, 10, 210),
            outline=(255, 255, 255, 95),
            width=2,
        )

        padding_left = 42
        padding_right = 18
        padding_top = 28
        padding_bottom = 48

        graph_left = left + padding_left
        graph_right = right - padding_right
        graph_top = top + padding_top
        graph_bottom = bottom - padding_bottom

        elevations = self.profile_elevations
        distances = self.profile_distances
        min_elevation = float(elevations.min())
        max_elevation = float(elevations.max())
        elevation_range = max(1.0, max_elevation - min_elevation)
        max_distance = max(1.0, float(distances[-1]))

        draw.line(
            (graph_left, graph_bottom, graph_right, graph_bottom),
            fill=(255, 255, 255, 100),
            width=1,
        )
        draw.line(
            (graph_left, graph_top, graph_left, graph_bottom),
            fill=(255, 255, 255, 100),
            width=1,
        )

        font = ImageFont.load_default()

        # Échelle altitude.
        altitude_ticks = 4
        for tick in range(altitude_ticks + 1):
            ratio = tick / altitude_ticks
            y = int(graph_bottom - ratio * (graph_bottom - graph_top))
            altitude = min_elevation + ratio * elevation_range
            draw.line(
                (graph_left, y, graph_right, y),
                fill=(255, 255, 255, 38),
                width=1,
            )
            draw.text(
                (left + 5, y - 6),
                f"{altitude:.0f}",
                fill=(255, 255, 255, 190),
                font=font,
            )

        # Échelle distance.
        distance_ticks = 5
        for tick in range(distance_ticks + 1):
            ratio = tick / distance_ticks
            x = int(graph_left + ratio * (graph_right - graph_left))
            distance_km = ratio * max_distance / 1000.0
            draw.line(
                (x, graph_top, x, graph_bottom),
                fill=(255, 255, 255, 30),
                width=1,
            )
            label = f"{distance_km:.0f}"
            draw.text(
                (x - 7, graph_bottom + 5),
                label,
                fill=(255, 255, 255, 190),
                font=font,
            )

        draw.text(
            (graph_right - 18, graph_bottom + 18),
            "km",
            fill=(255, 255, 255, 180),
            font=font,
        )
        draw.text(
            (left + 5, graph_top - 18),
            "m",
            fill=(255, 255, 255, 180),
            font=font,
        )

        visible_index = max(
            2,
            min(
                len(elevations),
                int(round(max(0.0, min(1.0, progress)) * (len(elevations) - 1))) + 1,
            ),
        )

        points = []
        for index in range(visible_index):
            x = graph_left + (distances[index] / max_distance) * (
                graph_right - graph_left
            )
            y = graph_bottom - (
                (elevations[index] - min_elevation) / elevation_range
            ) * (graph_bottom - graph_top)
            points.append((int(x), int(y)))

        if len(points) >= 2:
            fill_polygon = [(points[0][0], graph_bottom)] + points + [
                (points[-1][0], graph_bottom)
            ]
            red, green, blue = self.track_color
            draw.polygon(fill_polygon, fill=(red, green, blue, 40))
            draw.line(points, fill=(red, green, blue, 255), width=3, joint="curve")

            marker_x, marker_y = points[-1]
            radius = 5
            draw.ellipse(
                (
                    marker_x - radius,
                    marker_y - radius,
                    marker_x + radius,
                    marker_y + radius,
                ),
                fill=(red, green, blue, 255),
                outline=(255, 255, 255, 230),
                width=1,
            )

        draw.text(
            (left + 14, top + 9),
            "PROFIL ALTIMETRIQUE",
            fill=(255, 255, 255, 235),
            font=font,
        )

        stats = self.profile_stats
        stats_text = (
            f"{stats['distance_km']:.1f} km   "
            f"D+ {stats['gain']:.0f} m   "
            f"D- {stats['loss']:.0f} m   "
            f"{stats['minimum']:.0f}-{stats['maximum']:.0f} m"
        )
        draw.text(
            (left + 14, bottom - 26),
            stats_text,
            fill=(255, 255, 255, 220),
            font=font,
        )

        return image

    def render_topdown_with_profile(self, frame_index, profile_progress):
        position, focal, view_up = self.top_down_camera()
        self.set_explicit_camera(position, focal, view_up)
        self.update_track(1.0, force=True)
        self.update_profile_marker(profile_progress)

        plotter = self.scene.plotter
        plotter.reset_camera_clipping_range()
        plotter.render()
        plotter.update()

        output_file = self.frame_path(frame_index)
        plotter.screenshot(str(output_file))

        with Image.open(output_file) as image:
            composed = self.draw_profile_inset(image, profile_progress)
            composed.save(output_file)

    def render_fade_frame(self, frame_index, source_frame, progress):
        progress = max(0.0, min(1.0, float(progress)))
        with Image.open(source_frame).convert("RGB") as image:
            overlay = Image.new("RGB", image.size, (0, 0, 0))
            composed = Image.blend(image, overlay, progress)
            composed.save(self.frame_path(frame_index))

    def render(self, frames=None):
        travel_frames = int(frames or config.TOTAL_FRAMES)
        fps = int(getattr(config, "FPS", 20))

        start_hold_frames = int(
            round(float(getattr(config, "START_HOLD_SECONDS", 3.0)) * fps)
        )
        arrival_hold_frames = int(
            round(float(getattr(config, "ARRIVAL_HOLD_SECONDS", 5.0)) * fps)
        )
        flatten_frames = int(
            round(float(getattr(config, "FLATTEN_TRANSITION_SECONDS", 3.0)) * fps)
        )
        profile_animation_frames = int(
            round(float(getattr(config, "PROFILE_ANIMATION_SECONDS", 6.0)) * fps)
        )
        profile_hold_frames = int(
            round(float(getattr(config, "PROFILE_HOLD_SECONDS", 4.0)) * fps)
        )
        fade_frames = int(
            round(float(getattr(config, "FADE_OUT_SECONDS", 2.0)) * fps)
        )

        total = (
            start_hold_frames
            + travel_frames
            + arrival_hold_frames
            + flatten_frames
            + profile_animation_frames
            + profile_hold_frames
            + fade_frames
        )

        print(
            "Séquence V15 : "
            f"{start_hold_frames} départ + "
            f"{travel_frames} parcours + "
            f"{arrival_hold_frames} arrivée + "
            f"{flatten_frames} mise à plat + "
            f"{profile_animation_frames} profil + "
            f"{profile_hold_frames} maintien + "
            f"{fade_frames} fondu = "
            f"{total} images"
        )

        self.clear_frames()
        plotter = self.scene.plotter
        plotter.show(auto_close=False, interactive=False)
        self.create_track_actor()

        if bool(getattr(config, "LEADER_ENABLED", False)):
            self.leader.create()

        frame_index = 0

        # Départ fixe : premier point exactement centré, leader immobile.
        for hold_index in range(start_hold_frames):
            self.render_start_frame(
                frame_index,
                force_track=(hold_index == 0),
            )
            frame_index += 1

        # Parcours : transition douce du gros plan vers la caméra Director.
        start_blend_frames = max(
            1,
            int(
                round(
                    float(
                        getattr(
                            config,
                            "START_CAMERA_BLEND_SECONDS",
                            getattr(
                                config,
                                "SLOWDOWN_START_SECONDS",
                                3.0,
                            ),
                        )
                    )
                    * fps
                )
            ),
        )

        for travel_index in range(travel_frames):
            linear_progress = travel_index / max(1, travel_frames - 1)
            progress = self.eased_progress(linear_progress)

            start_camera_blend = min(
                1.0,
                travel_index / max(1, start_blend_frames),
            )

            finish_blend_frames = max(
                1,
                int(
                    round(
                        float(
                            getattr(
                                config,
                                "SLOWDOWN_END_SECONDS",
                                3.0,
                            )
                        )
                        * fps
                    )
                ),
            )
            finish_camera_blend = max(
                0.0,
                min(
                    1.0,
                    (
                        travel_index
                        - (travel_frames - finish_blend_frames)
                    )
                    / max(1, finish_blend_frames),
                ),
            )

            self.render_route_frame(
                frame_index,
                progress,
                start_camera_blend=(
                    start_camera_blend
                    if finish_camera_blend <= 0.0
                    else None
                ),
                finish_camera_blend=(
                    finish_camera_blend
                    if finish_camera_blend > 0.0
                    else None
                ),
            )
            frame_index += 1

            if travel_index % 10 == 0 or travel_index == travel_frames - 1:
                print(
                    f"\rParcours {travel_index + 1}/{travel_frames}",
                    end="",
                    flush=True,
                )
        print()

        # Pause sur l'arrivée avec disparition progressive de la traînée.
        trail_fade_enabled = bool(
            getattr(
                config,
                "LEADER_FADE_TRAIL_ON_ARRIVAL",
                True,
            )
        )
        trail_fade_frames = max(
            1,
            int(
                round(
                    float(
                        getattr(
                            config,
                            "LEADER_TRAIL_FADE_DURATION",
                            1.5,
                        )
                    )
                    * fps
                )
            ),
        )

        for hold_index in range(arrival_hold_frames):
            trail_fade_progress = None

            if trail_fade_enabled:
                trail_fade_progress = min(
                    1.0,
                    (hold_index + 1)
                    / max(1, trail_fade_frames),
                )

            self.render_route_frame(
                frame_index,
                1.0,
                force_track=(hold_index == 0),
                trail_fade_progress=trail_fade_progress,
                finish_camera_blend=1.0,
            )
            frame_index += 1

        arrival_position, arrival_focal, _ = self.camera_path.camera_at_progress(1.0)
        arrival_position = np.asarray(arrival_position, dtype=float)
        arrival_focal = np.asarray(arrival_focal, dtype=float)

        # Montée vers une vue verticale du parcours complet.
        for flatten_index in range(flatten_frames):
            progress = flatten_index / max(1, flatten_frames - 1)
            self.render_flatten_transition(
                frame_index,
                progress,
                arrival_position,
                arrival_focal,
            )
            frame_index += 1

        # Profil animé dans un coin de la carte vue du dessus.
        for profile_index in range(profile_animation_frames):
            progress = profile_index / max(1, profile_animation_frames - 1)
            self.render_topdown_with_profile(frame_index, progress)
            frame_index += 1

            if profile_index % 20 == 0 or profile_index == profile_animation_frames - 1:
                print(
                    f"\rProfil {profile_index + 1}/{profile_animation_frames}",
                    end="",
                    flush=True,
                )
        print()

        # Maintien final du profil complet.
        for _ in range(profile_hold_frames):
            self.render_topdown_with_profile(frame_index, 1.0)
            frame_index += 1

        if fade_frames > 0:
            source_frame = self.frame_path(frame_index - 1)
            for fade_index in range(fade_frames):
                progress = (fade_index + 1) / fade_frames
                self.render_fade_frame(frame_index, source_frame, progress)
                frame_index += 1

        print("Rendu des images terminé :", frame_index)
