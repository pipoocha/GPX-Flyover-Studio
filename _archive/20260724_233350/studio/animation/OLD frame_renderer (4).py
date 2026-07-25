from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
from PIL import Image

import config
from studio.animation.progress_path import ProgressPath
from studio.leader.leader import LeaderMarker


class FrameRenderer:
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
        self.track_color = self.hex_to_rgb(str(getattr(config, "TRACK_COLOR", "#FC4C02")))
        self.leader = LeaderMarker(scene=self.scene, path_coords=self.path_coords)

    @staticmethod
    def hex_to_rgb(value):
        value = value.strip().lstrip("#")
        if len(value) != 6:
            return 252, 76, 2
        try:
            return int(value[0:2],16), int(value[2:4],16), int(value[4:6],16)
        except ValueError:
            return 252, 76, 2

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

    def update_track(self, progress, force=False):
        total_segments = len(self.track_rgba)
        if bool(getattr(config, "TRACE_PROGRESSIVE", True)):
            visible_segments = int(round(max(0.0, min(1.0, progress)) * total_segments))
        else:
            visible_segments = total_segments
        if not force and visible_segments == self.visible_segment_count:
            return
        self.track_rgba[:, 3] = 0
        if visible_segments > 0:
            self.track_rgba[:visible_segments, 3] = 255
        self.track_mesh.cell_data["track_rgba"] = self.track_rgba
        self.track_mesh.Modified()
        self.visible_segment_count = visible_segments

    def save_frame(self, frame_index):
        self.scene.plotter.screenshot(str(self.output_dir / f"frame_{frame_index:05d}.png"))

    def render_3d_frame(self, frame_index, progress, force_track=False):
        position, focal_point, _ = self.camera_path.camera_at_progress(progress)
        self.scene.set_camera(position=tuple(position), focal_point=tuple(focal_point))
        self.update_track(progress, force=force_track)
        if bool(getattr(config, "LEADER_ENABLED", False)):
            self.leader.update(progress)
        plotter = self.scene.plotter
        plotter.reset_camera_clipping_range()
        plotter.render()
        plotter.update()
        self.save_frame(frame_index)

    @staticmethod
    def profile_distances(path_coords):
        differences = np.diff(path_coords[:, :3], axis=0)
        lengths = np.linalg.norm(differences, axis=1)
        return np.insert(np.cumsum(lengths), 0, 0.0)

    @staticmethod
    def profile_stats(distances, elevations):
        changes = np.diff(elevations)
        return {
            "distance_km": float(distances[-1] / 1000.0),
            "gain": float(changes[changes > 0].sum()),
            "loss": float(-changes[changes < 0].sum()),
            "minimum": float(elevations.min()),
            "maximum": float(elevations.max()),
        }

    def render_profile_frame(self, frame_index, progress):
        width = int(getattr(config, "WINDOW_WIDTH", 1280))
        height = int(getattr(config, "WINDOW_HEIGHT", 720))
        distances = self.profile_distances(self.path_coords)
        elevations = self.path_coords[:, 2]
        distances_km = distances / 1000.0
        stats = self.profile_stats(distances, elevations)
        visible_index = max(2, min(len(elevations), int(round(progress * (len(elevations) - 1))) + 1))
        fig = plt.figure(figsize=(width/100.0, height/100.0), dpi=100, facecolor="#101010")
        ax = fig.add_axes([0.08, 0.20, 0.88, 0.64])
        ax.set_facecolor("#101010")
        margin = max(80.0, (elevations.max() - elevations.min()) * 0.12)
        ax.plot(distances_km[:visible_index], elevations[:visible_index], color="#FC4C02", linewidth=3.0)
        ax.fill_between(distances_km[:visible_index], elevations[:visible_index], elevations.min() - margin, color="#FC4C02", alpha=0.18)
        ax.scatter([distances_km[visible_index-1]], [elevations[visible_index-1]], color="#FC4C02", s=70, zorder=5)
        ax.set_xlim(0.0, max(0.1, distances_km[-1]))
        ax.set_ylim(elevations.min() - margin, elevations.max() + margin)
        ax.set_xlabel("Distance (km)", color="white", fontsize=12)
        ax.set_ylabel("Altitude (m)", color="white", fontsize=12)
        ax.tick_params(colors="white", labelsize=10)
        ax.grid(alpha=0.18, linewidth=0.7)
        for spine in ax.spines.values():
            spine.set_color("#777777")
        fig.text(0.08, 0.91, str(getattr(config, "PROJECT_TITLE", "Profil altimétrique")), color="white", fontsize=20, weight="bold")
        fig.text(0.08, 0.08, f"Distance {stats['distance_km']:.1f} km    D+ {stats['gain']:.0f} m    D− {stats['loss']:.0f} m    Min {stats['minimum']:.0f} m    Max {stats['maximum']:.0f} m", color="white", fontsize=13)
        output_file = (
            self.output_dir
            / f"frame_{frame_index:05d}.png"
        )

        fig.savefig(
            output_file,
            facecolor=fig.get_facecolor(),
            transparent=False,
        )

        plt.close(fig)

        # Matplotlib peut enregistrer les PNG avec un canal alpha (RGBA),
        # alors que les captures PyVista sont généralement en RGB.
        # On force donc toutes les images du profil en RGB 24 bits.
        with Image.open(output_file) as image:
            rgb_image = image.convert("RGB")
            rgb_image.save(output_file)

    def render(self, frames=None):
        travel_frames = int(frames or config.TOTAL_FRAMES)
        fps = int(getattr(config, "FPS", 20))
        start_hold_frames = int(round(float(getattr(config, "START_HOLD_SECONDS", 3.0)) * fps))
        arrival_hold_frames = int(round(float(getattr(config, "ARRIVAL_HOLD_SECONDS", 5.0)) * fps))
        profile_frames = int(round(float(getattr(config, "PROFILE_OUTRO_SECONDS", 6.0)) * fps))
        total = start_hold_frames + travel_frames + arrival_hold_frames + profile_frames
        print(f"Séquence vidéo : {start_hold_frames} départ + {travel_frames} parcours + {arrival_hold_frames} arrivée + {profile_frames} profil = {total} images")
        self.clear_frames()
        plotter = self.scene.plotter
        plotter.show(auto_close=False, interactive=False)
        self.create_track_actor()
        if bool(getattr(config, "LEADER_ENABLED", False)):
            self.leader.create()
        frame_index = 0
        for hold_index in range(start_hold_frames):
            self.render_3d_frame(frame_index, 0.0, force_track=(hold_index == 0))
            frame_index += 1
        for travel_index in range(travel_frames):
            progress = travel_index / max(1, travel_frames - 1)
            self.render_3d_frame(frame_index, progress)
            frame_index += 1
            if travel_index % 10 == 0 or travel_index == travel_frames - 1:
                print(f"\rParcours {travel_index + 1}/{travel_frames}", end="", flush=True)
        print()
        for _ in range(arrival_hold_frames):
            self.render_3d_frame(frame_index, 1.0, force_track=True)
            frame_index += 1
        for profile_index in range(profile_frames):
            progress = profile_index / max(1, profile_frames - 1)
            self.render_profile_frame(frame_index, progress)
            frame_index += 1
            if profile_index % 20 == 0 or profile_index == profile_frames - 1:
                print(f"\rProfil {profile_index + 1}/{profile_frames}", end="", flush=True)
        print()
        print("Rendu des images terminé :", frame_index)
