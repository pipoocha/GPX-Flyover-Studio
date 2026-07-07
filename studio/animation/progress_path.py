import numpy as np


class ProgressPath:
    def __init__(self, path_coords):
        self.coords = np.asarray(path_coords, dtype=float)
        self.distances = self._compute_distances()
        self.total_distance = self.distances[-1]

    def _compute_distances(self):
        if len(self.coords) < 2:
            return np.array([0.0])

        diffs = np.diff(self.coords[:, :3], axis=0)
        lengths = np.linalg.norm(diffs, axis=1)

        return np.insert(np.cumsum(lengths), 0, 0.0)

    def visible_path(self, progress):
        progress = max(0.0, min(1.0, progress))

        if len(self.coords) < 2:
            return self.coords

        target_distance = progress * self.total_distance

        index = np.searchsorted(self.distances, target_distance)

        index = max(1, min(index, len(self.coords) - 1))

        previous_distance = self.distances[index - 1]
        next_distance = self.distances[index]

        segment_length = max(1e-9, next_distance - previous_distance)

        t = (target_distance - previous_distance) / segment_length

        p0 = self.coords[index - 1]
        p1 = self.coords[index]

        current_point = p0 * (1.0 - t) + p1 * t

        visible = np.vstack(
            [
                self.coords[:index],
                current_point,
            ]
        )

        return visible