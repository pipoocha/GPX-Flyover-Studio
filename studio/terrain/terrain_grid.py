from dataclasses import dataclass
import numpy as np


@dataclass
class TerrainGrid:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray

    @property
    def shape(self):
        return self.z.shape

    @classmethod
    def procedural_mountain(cls, width=5000, height=5000, resolution=50):
        xs = np.arange(0, width, resolution)
        ys = np.arange(0, height, resolution)

        X, Y = np.meshgrid(xs, ys)

        cx = width / 2
        cy = height / 2

        Z = (
            800 * np.exp(-(((X - cx) ** 2 + (Y - cy) ** 2) / (2 * 900 ** 2)))
            + 350 * np.exp(-(((X - 1500) ** 2 + (Y - 3600) ** 2) / (2 * 600 ** 2)))
            + 220 * np.sin(X / 450) * np.cos(Y / 600)
        )

        Z = Z - Z.min()

        return cls(X, Y, Z)