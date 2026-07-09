import math
import numpy as np


class OrientationController:
    def __init__(self, coords, mode="route", angle=0):
        self.coords = np.asarray(coords, dtype=float)
        self.mode = str(mode).lower()
        self.angle = float(angle)

    def direction(self):
        if self.mode == "north":
            return np.array([0.0, 1.0, 0.0])

        if self.mode == "fixed":
            radians = math.radians(self.angle)
            return np.array(
                [
                    math.sin(radians),
                    math.cos(radians),
                    0.0,
                ],
                dtype=float,
            )

        return self.route_direction()

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

        norm = np.linalg.norm(direction)

        if norm < 1:
            return np.array([0.0, 1.0, 0.0])

        return direction / norm