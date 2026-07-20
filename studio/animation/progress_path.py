import numpy as np


class ProgressPath:
    def __init__(self, path_coords):
        self.coords = np.asarray(path_coords, dtype=float)

        if len(self.coords) == 0:
            raise ValueError("La trajectoire est vide.")

        self.distances = self._compute_distances()
        self.total_distance = float(self.distances[-1])

    def _compute_distances(self):
        if len(self.coords) < 2:
            return np.array([0.0], dtype=float)

        differences = np.diff(self.coords[:, :3], axis=0)
        lengths = np.linalg.norm(differences, axis=1)

        return np.insert(
            np.cumsum(lengths),
            0,
            0.0,
        )

    @staticmethod
    def clamp_progress(progress):
        return max(0.0, min(1.0, float(progress)))

    def point_at(self, progress):
        progress = self.clamp_progress(progress)

        if len(self.coords) == 1 or self.total_distance <= 0:
            return self.coords[0].copy(), 0

        target_distance = progress * self.total_distance

        index = int(
            np.searchsorted(
                self.distances,
                target_distance,
                side="left",
            )
        )

        index = max(
            1,
            min(index, len(self.coords) - 1),
        )

        previous_distance = self.distances[index - 1]
        next_distance = self.distances[index]

        segment_length = max(
            1e-9,
            next_distance - previous_distance,
        )

        local_progress = (
            target_distance - previous_distance
        ) / segment_length

        point_0 = self.coords[index - 1]
        point_1 = self.coords[index]

        current_point = (
            point_0 * (1.0 - local_progress)
            + point_1 * local_progress
        )

        return current_point, index

    def visible_path(self, progress):
        progress = self.clamp_progress(progress)

        if len(self.coords) < 2:
            return self.coords.copy()

        current_point, index = self.point_at(progress)

        return np.vstack(
            [
                self.coords[:index],
                current_point,
            ]
        )