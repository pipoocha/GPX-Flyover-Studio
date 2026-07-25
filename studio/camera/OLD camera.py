from __future__ import annotations

import numpy as np


class V5Camera:
    """Caméra unique V5, pilotée directement par ProjectConfig."""

    def __init__(self, path_coords, camera_config):
        self.coords = np.asarray(path_coords, dtype=float)
        if len(self.coords) < 2:
            raise ValueError("La trajectoire doit contenir au moins deux points.")

        self.config = camera_config
        self.center = self.coords.mean(axis=0)
        self.min_xy = self.coords[:, :2].min(axis=0)
        self.max_xy = self.coords[:, :2].max(axis=0)
        extent = self.max_xy - self.min_xy
        self.route_size = float(max(extent[0], extent[1], 1.0))
        self.min_z = float(self.coords[:, 2].min())
        self.max_z = float(self.coords[:, 2].max())
        self.relief = max(1.0, self.max_z - self.min_z)

        self.previous_position = None
        self.previous_focal = None
        self.previous_side = 1.0

    @staticmethod
    def clamp(value, minimum, maximum):
        return max(minimum, min(maximum, float(value)))

    @staticmethod
    def normalize(vector):
        vector = np.asarray(vector, dtype=float)
        norm = np.linalg.norm(vector)
        if norm < 1e-9:
            return np.array([0.0, 1.0, 0.0], dtype=float)
        return vector / norm

    def index_at_progress(self, progress):
        progress = self.clamp(progress, 0.0, 1.0)
        return int(round(progress * (len(self.coords) - 1)))

    def direction_between(self, first, second):
        first = max(0, min(len(self.coords) - 1, int(first)))
        second = max(0, min(len(self.coords) - 1, int(second)))
        direction = self.coords[second] - self.coords[first]
        direction[2] = 0.0
        return self.normalize(direction)

    def local_direction(self, index):
        window = max(8, int(self.config.look_ahead // 8))
        return self.direction_between(index - window, index + window)

    def local_relief(self, index):
        window = max(20, int(self.config.look_ahead // 2))
        start = max(0, index - window)
        end = min(len(self.coords), index + window + 1)
        values = self.coords[start:end, 2]
        return float(values.max() - values.min())

    def local_max_altitude(self, index):
        window = max(20, int(self.config.look_ahead // 2))
        start = max(0, index - window)
        end = min(len(self.coords), index + window + 1)
        return float(self.coords[start:end, 2].max())

    def turn_side(self, index):
        window = max(8, int(self.config.look_ahead // 10))
        before = self.direction_between(index - window, index)
        after = self.direction_between(index, index + window)
        cross = before[0] * after[1] - before[1] * after[0]
        target = self.previous_side if abs(cross) < 0.03 else (-1.0 if cross > 0 else 1.0)
        self.previous_side = self.previous_side * 0.94 + target * 0.06
        return self.previous_side

    def smooth(self, previous, current):
        alpha = self.clamp(self.config.smoothing, 0.01, 1.0)
        current = np.asarray(current, dtype=float)
        if previous is None:
            return current.copy()
        return np.asarray(previous, dtype=float) * (1.0 - alpha) + current * alpha

    def endpoint_wide_factor(self, progress):
        window = 0.06
        if progress < window:
            x = 1.0 - progress / window
        elif progress > 1.0 - window:
            x = (progress - (1.0 - window)) / window
        else:
            return 0.0
        x = self.clamp(x, 0.0, 1.0)
        return x * x * (3.0 - 2.0 * x)

    def camera_at_progress(self, progress):
        progress = self.clamp(progress, 0.0, 1.0)
        index = self.index_at_progress(progress)
        active = self.coords[index]

        look_steps = max(2, int(self.config.look_ahead))
        middle_index = min(len(self.coords) - 1, index + max(1, look_steps // 2))
        look_index = min(len(self.coords) - 1, index + look_steps)
        middle = self.coords[middle_index]
        look = self.coords[look_index]

        direction = self.local_direction(index)
        side = np.array([-direction[1], direction[0], 0.0], dtype=float)

        local_relief = self.local_relief(index)
        relief_factor = self.clamp(local_relief / self.relief, 0.0, 1.0)

        distance = self.clamp(
            self.route_size * self.config.distance.scale * (1.0 + 0.18 * relief_factor),
            self.config.distance.minimum,
            self.config.distance.maximum,
        )
        height = self.clamp(
            self.route_size * self.config.height.scale * (1.0 + 0.22 * relief_factor),
            self.config.height.minimum,
            self.config.height.maximum,
        )
        lateral = self.clamp(
            distance * self.config.lateral.scale,
            self.config.lateral.minimum,
            self.config.lateral.maximum,
        )

        moving_center = active * 0.58 + middle * 0.27 + look * 0.15
        position = moving_center - direction * distance
        position += side * lateral * self.turn_side(index)

        clearance = max(160.0, height * 0.18)
        position[2] = max(active[2] + height, self.local_max_altitude(index) + clearance)

        focal = active * 0.28 + middle * 0.34 + look * 0.38
        focal[2] += max(40.0, height * 0.06)

        wide = self.endpoint_wide_factor(progress)
        if wide > 0.0:
            anchor = self.coords[0] if progress < 0.5 else self.coords[-1]
            wide_distance = self.clamp(self.route_size * 0.55, 2200.0, 5200.0)
            wide_height = self.clamp(self.route_size * 0.26, 1000.0, 2800.0)
            wide_position = anchor - direction * wide_distance + side * min(700.0, wide_distance * 0.10)
            wide_position[2] = max(anchor[2] + wide_height, self.max_z + 260.0)
            wide_focal = anchor.copy()
            position = position * (1.0 - wide) + wide_position * wide
            focal = focal * (1.0 - wide) + wide_focal * wide

        position = self.smooth(self.previous_position, position)
        focal = self.smooth(self.previous_focal, focal)
        self.previous_position = position.copy()
        self.previous_focal = focal.copy()

        return position, focal, index
