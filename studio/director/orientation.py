import math
import numpy as np


class OrientationController:
    def __init__(self, coords, mode="route", angle=0):
        self.coords = np.asarray(coords, dtype=float)
        self.mode = str(mode).lower()
        self.angle = float(angle)

        self.previous_direction = None

    def direction_at_progress(self, progress):
        if self.mode == "north":
            return np.array([0.0, 1.0, 0.0])

        if self.mode == "fixed":
            return self.fixed_direction(self.angle)

        if self.mode == "auto":
            return self.auto_direction(progress)

        return self.route_direction()

    def fixed_direction(self, angle):
        radians = math.radians(angle)

        return np.array(
            [
                math.sin(radians),
                math.cos(radians),
                0.0,
            ],
            dtype=float,
        )

    def route_direction(self):
        xy = self.coords[:, :2]
        xy_centered = xy - xy.mean(axis=0)

        cov = np.cov(xy_centered.T)
        eigenvalues, eigenvectors = np.linalg.eig(cov)

        main_vector = eigenvectors[:, np.argmax(eigenvalues)]

        direction = np.array(
            [
                main_vector[0],
                main_vector[1],
                0.0,
            ],
            dtype=float,
        )

        start_to_end = self.coords[-1] - self.coords[0]
        start_to_end[2] = 0

        if np.dot(direction, start_to_end) < 0:
            direction *= -1

        return self.normalize(direction)

    def local_route_direction(self, progress, window=250):
        max_index = len(self.coords) - 1
        index = int(progress * max_index)

        i0 = max(0, index - window)
        i1 = min(max_index, index + window)

        if i1 <= i0:
            return self.route_direction()

        direction = self.coords[i1] - self.coords[i0]
        direction[2] = 0

        return self.normalize(direction)

    def auto_direction(self, progress):
        target = self.local_route_direction(progress)

        if self.previous_direction is None:
            self.previous_direction = target
            return target

        # Empêche les inversions brutales 180°
        if np.dot(self.previous_direction, target) < 0:
            target *= -1

        alpha = 0.015

        direction = (
            self.previous_direction * (1.0 - alpha)
            + target * alpha
        )

        direction = self.normalize(direction)

        self.previous_direction = direction

        return direction

    def normalize(self, direction):
        norm = np.linalg.norm(direction)

        if norm < 1:
            return np.array([0.0, 1.0, 0.0])

        return direction / norm