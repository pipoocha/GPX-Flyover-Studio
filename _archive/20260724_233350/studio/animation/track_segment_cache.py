import numpy as np
import pyvista as pv

from studio.scene.track import Track


class TrackSegmentCache:
    def __init__(
        self,
        path_coords,
        segment_points=20,
        radius=7,
        sides=8,
        mode="line",
    ):
        self.path_coords = np.asarray(path_coords, dtype=float)
        self.segment_points = max(2, int(segment_points))
        self.radius = radius
        self.sides = sides
        self.mode = mode
        self.segments = []

    def build(self):
        self.segments = []

        total = len(self.path_coords)

        for start in range(0, total - 1, self.segment_points - 1):
            end = min(total, start + self.segment_points)

            segment = self.path_coords[start:end]

            if len(segment) < 2:
                continue

            if self.mode == "line":
                mesh = pv.lines_from_points(segment)
            else:
                mesh = Track(
                    segment,
                    radius=self.radius,
                    sides=self.sides,
                ).to_mesh()

            self.segments.append(mesh)

        print(f"Segments trace pré-calculés : {len(self.segments)}")

        return self.segments

    def visible_segments(self, progress):
        if not self.segments:
            return []

        progress = max(0.0, min(1.0, progress))
        count = int(progress * len(self.segments))

        return self.segments[: max(1, count)]