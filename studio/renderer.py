from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

import matplotlib.pyplot as plt

from studio.overlay import Overlay
from studio.profile import ElevationProfile


class Renderer:
    def __init__(self, points, xs, ys, camera_frames, background_file, config, frames_dir):
        self.points = points
        self.xs = xs
        self.ys = ys
        self.camera_frames = camera_frames
        self.background_file = Path(background_file)
        self.config = config
        self.frames_dir = Path(frames_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        self.overlay = Overlay(config)
        self.distances = self.compute_distances()
        self.profile = ElevationProfile(points, self.distances)

    def haversine(self, p1, p2):
        r = 6371000
        lat1, lon1 = radians(p1["lat"]), radians(p1["lon"])
        lat2, lon2 = radians(p2["lat"]), radians(p2["lon"])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return r * c

    def compute_distances(self):
        distances = [0.0]

        for i in range(1, len(self.points)):
            distances.append(
                distances[-1] + self.haversine(self.points[i - 1], self.points[i])
            )

        return distances

    def format_time(self, seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def speed_at(self, index):
        if index <= 0:
            return 0.0

        t1 = self.points[index - 1].get("time")
        t2 = self.points[index].get("time")

        if t1 is None or t2 is None:
            return 0.0

        seconds = (t2 - t1).total_seconds()

        if seconds <= 0:
            return 0.0

        d = self.distances[index] - self.distances[index - 1]
        return (d / 1000) / (seconds / 3600)

    def elapsed_at(self, index):
        start = self.points[0].get("time")
        current = self.points[index].get("time")

        if start is None or current is None:
            return "00:00:00"

        return self.format_time((current - start).total_seconds())

    def render_frames(self):
        route_color = self.config.get("route", "color", default="#FC4C02")
        route_width = self.config.get("route", "width", default=6)

        bg = plt.imread(self.background_file)

        full_xmin = min(self.xs)
        full_xmax = max(self.xs)
        full_ymin = min(self.ys)
        full_ymax = max(self.ys)

        size = max(full_xmax - full_xmin, full_ymax - full_ymin)
        full_extent = [
            full_xmin - size * 0.20,
            full_xmax + size * 0.20,
            full_ymin - size * 0.20,
            full_ymax + size * 0.20,
        ]

        frame_files = []

        for cam in self.camera_frames:
            i = cam["frame"]
            index = cam["point_index"]

            fig, ax = plt.subplots(figsize=(16, 9))
            ax.imshow(bg, extent=full_extent)

            ax.set_xlim(*cam["xlim"])
            ax.set_ylim(*cam["ylim"])

            # Trace totale discrète
            ax.plot(self.xs, self.ys, color="black", linewidth=route_width + 5, alpha=0.45)
            ax.plot(self.xs, self.ys, color="#777777", linewidth=max(1, route_width - 1), alpha=0.55)

            # Trace parcourue orange
            ax.plot(self.xs[:index], self.ys[:index], color="black", linewidth=route_width + 6, alpha=0.45)
            ax.plot(self.xs[:index], self.ys[:index], color=route_color, linewidth=route_width)

            # Points
            ax.scatter(self.xs[index], self.ys[index], color=route_color, s=180, zorder=10)
            ax.scatter(self.xs[0], self.ys[0], color="lime", s=100, zorder=10)
            ax.scatter(self.xs[-1], self.ys[-1], color="red", s=100, zorder=10)

            progress = index / max(1, len(self.xs) - 1)

            overlay_data = {
                "progress": progress,
                "distance_km": self.distances[index] / 1000,
                "altitude": self.points[index]["ele"],
                "speed_kmh": self.speed_at(index),
                "elapsed": self.elapsed_at(index),
            }

            self.overlay.draw(ax, overlay_data)
            self.profile.draw(ax, index)

            ax.axis("off")
            plt.tight_layout()

            frame_file = self.frames_dir / f"frame_{i:05d}.png"
            plt.savefig(frame_file, dpi=120)
            plt.close(fig)

            frame_files.append(frame_file)

            if i % 30 == 0:
                print(f"Frame {i}/{len(self.camera_frames)}")

        return frame_files