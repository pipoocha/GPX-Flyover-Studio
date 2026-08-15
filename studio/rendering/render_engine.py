from __future__ import annotations

import numpy as np
import pyvista as pv

import config
from studio.leader.leader import LeaderMarker


class RenderEngine:
    """Noyau commun au preview et au rendu vidéo.

    Il possède et met à jour la caméra de parcours, la trace progressive et
    le leader. Les lecteurs PreviewPlayer et FrameRenderer ne calculent plus
    ces éléments séparément.
    """

    def __init__(self, scene, camera_path, path_coords):
        self.scene = scene
        self.camera_path = camera_path
        self.path_coords = np.asarray(path_coords, dtype=float)
        if len(self.path_coords) < 2:
            raise ValueError("La trajectoire doit contenir au moins deux points.")

        self.track_z_offset = float(getattr(config, "TRACK_Z_OFFSET", 8.0))
        self.track_line_width = float(getattr(config, "TRACK_LINE_WIDTH", 1.5))
        self.track_color_hex = str(getattr(config, "TRACK_COLOR", "#FC4C02"))
        self.track_color = self.hex_to_rgb(self.track_color_hex)

        self.track_mesh = None
        self.track_actor = None
        self.track_rgba = None
        self.track_halo_mesh = None
        self.track_halo_actor = None
        self.track_halo_rgba = None
        self.visible_segment_count = -1
        self.leader = LeaderMarker(scene=self.scene, path_coords=self.path_coords)

    @staticmethod
    def hex_to_rgb(value):
        value = str(value).strip().lstrip("#")
        if len(value) != 6:
            return 252, 76, 2
        try:
            return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))
        except ValueError:
            return 252, 76, 2

    @staticmethod
    def smootherstep(value):
        value = max(0.0, min(1.0, float(value)))
        return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)

    def create(self):
        self.create_track_actor()
        if bool(getattr(config, "LEADER_ENABLED", False)):
            self.leader.create()

    def create_track_actor(self):
        if self.track_actor is not None:
            return self.track_actor

        points = self.path_coords.copy()
        points[:, 2] += self.track_z_offset
        halo_points = self.path_coords.copy()
        # Le halo doit rester sous le coeur orange. Sur certains angles de fin
        # de parcours, deux tubes sur la meme geometrie provoquaient un conflit
        # de profondeur et le halo sombre pouvait recouvrir toute la trace.
        halo_points[:, 2] += max(0.0, self.track_z_offset - 2.5)
        segment_count = len(points) - 1
        lines = np.empty(segment_count * 3, dtype=np.int64)
        lines[0::3] = 2
        lines[1::3] = np.arange(segment_count, dtype=np.int64)
        lines[2::3] = np.arange(1, segment_count + 1, dtype=np.int64)

        red, green, blue = self.track_color

        # Halo externe sombre : il sépare la trace des forêts, rochers et neige.
        self.track_halo_mesh = pv.PolyData(halo_points, lines=lines.copy())
        self.track_halo_rgba = np.zeros((segment_count, 4), dtype=np.uint8)
        self.track_halo_rgba[:, :3] = (70, 42, 28)
        self.track_halo_mesh.cell_data["track_halo_rgba"] = self.track_halo_rgba
        halo_width = max(4.5, self.track_line_width * 3.2)
        self.track_halo_actor = self.scene.add_mesh(
            self.track_halo_mesh,
            scalars="track_halo_rgba",
            rgba=True,
            preference="cell",
            line_width=halo_width,
            render_lines_as_tubes=True,
            lighting=False,
        )

        # Coeur orange plus épais qu'avant, rendu comme un tube antialiasé.
        self.track_mesh = pv.PolyData(points, lines=lines)
        self.track_rgba = np.zeros((segment_count, 4), dtype=np.uint8)
        self.track_rgba[:, 0] = red
        self.track_rgba[:, 1] = green
        self.track_rgba[:, 2] = blue
        self.track_mesh.cell_data["track_rgba"] = self.track_rgba
        core_width = max(2.4, self.track_line_width * 1.65)
        self.track_actor = self.scene.add_mesh(
            self.track_mesh,
            scalars="track_rgba",
            rgba=True,
            preference="cell",
            line_width=core_width,
            render_lines_as_tubes=True,
            lighting=False,
        )
        return self.track_actor

    def update_track(self, progress, force=False, minimum_segments=0):
        self.create_track_actor()
        total_segments = len(self.track_rgba)
        if bool(getattr(config, "TRACE_PROGRESSIVE", True)):
            visible_segments = int(round(max(0.0, min(1.0, float(progress))) * total_segments))
        else:
            visible_segments = total_segments
        visible_segments = max(int(minimum_segments), min(total_segments, visible_segments))
        if not force and visible_segments == self.visible_segment_count:
            return

        self.track_rgba[:, 3] = 0
        self.track_halo_rgba[:, 3] = 0
        if visible_segments:
            self.track_rgba[:visible_segments, 3] = 255
            self.track_halo_rgba[:visible_segments, 3] = 150
        self.track_mesh.cell_data["track_rgba"] = self.track_rgba
        self.track_halo_mesh.cell_data["track_halo_rgba"] = self.track_halo_rgba
        self.track_mesh.Modified()
        self.track_halo_mesh.Modified()
        try:
            self.track_actor.mapper.Update()
            self.track_halo_actor.mapper.Update()
        except Exception:
            pass
        self.visible_segment_count = visible_segments

    def start_camera(self):
        position, focal_point, _ = self.camera_path.camera_at_progress(0.0)
        position = np.asarray(position, dtype=float)
        focal_point = np.asarray(focal_point, dtype=float)
        target = self.path_coords[0].copy()
        target[2] += float(getattr(config, "LEADER_Z_OFFSET", 18.0))

        vector = position - focal_point
        normal_distance = float(np.linalg.norm(vector))
        if normal_distance < 1e-9:
            vector = np.array([0.0, -1.0, 0.35], dtype=float)
            normal_distance = float(np.linalg.norm(vector))
        direction = vector / normal_distance
        zoom_factor = max(0.20, min(1.0, float(getattr(config, "START_CAMERA_ZOOM_FACTOR", 0.45))))
        view_angle = float(getattr(self.scene.plotter.camera, "view_angle", 30.0))
        leader_radius = float(getattr(config, "LEADER_RADIUS", 20.0))
        halo_scale = max(1.0, float(getattr(config, "LEADER_HALO_SCALE", 1.8)))
        screen_fraction = max(0.08, min(0.30, float(getattr(config, "START_LEADER_SCREEN_FRACTION", 0.16))))
        visible_radius = leader_radius * halo_scale
        half_angle = np.radians(max(0.5, view_angle * screen_fraction * 0.5))
        safe_distance = visible_radius / max(1e-6, np.tan(half_angle))
        distance = max(normal_distance * zoom_factor, safe_distance)
        return target + direction * distance, target

    def route_camera(self, progress):
        position, focal, _ = self.camera_path.camera_at_progress(progress)
        return np.asarray(position, dtype=float), np.asarray(focal, dtype=float)

    def finish_camera(self):
        route_position, route_focal = self.route_camera(1.0)
        target = self.path_coords[-1].copy()
        target[2] += float(getattr(config, "LEADER_Z_OFFSET", 18.0))
        vector = route_position - route_focal
        distance = float(np.linalg.norm(vector))
        if distance < 1e-9:
            vector = np.array([0.0, -1.0, 0.35], dtype=float)
            distance = float(np.linalg.norm(vector))
        zoom = max(0.30, min(1.50, float(getattr(config, "FINISH_CAMERA_ZOOM_FACTOR", 0.70))))
        return target + vector / distance * distance * zoom, target

    def set_camera(self, progress, start_blend=None, finish_blend=None, start_centered=False):
        if start_centered:
            position, focal = self.start_camera()
        else:
            position, focal = self.route_camera(progress)
            if finish_blend is not None:
                target_position, target_focal = self.finish_camera()
                blend = self.smootherstep(finish_blend)
                position = position * (1.0 - blend) + target_position * blend
                focal = focal * (1.0 - blend) + target_focal * blend
            elif start_blend is not None:
                start_position, start_focal = self.start_camera()
                blend = self.smootherstep(start_blend)
                position = start_position * (1.0 - blend) + position * blend
                focal = start_focal * (1.0 - blend) + focal * blend
        self.scene.set_camera(position=tuple(position), focal_point=tuple(focal))
        self.scene.synchronize_viewport()
        return position, focal

    def update(self, progress, *, force_track=False, minimum_segments=0,
               start_blend=None, finish_blend=None, start_centered=False,
               trail_fade_progress=None):
        position, focal = self.set_camera(
            progress,
            start_blend=start_blend,
            finish_blend=finish_blend,
            start_centered=start_centered,
        )
        self.update_track(progress, force=force_track, minimum_segments=minimum_segments)
        if bool(getattr(config, "LEADER_ENABLED", False)):
            self.leader.update(progress)
            if trail_fade_progress is not None:
                self.leader.set_trail_fade(trail_fade_progress)
        return position, focal
