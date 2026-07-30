from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TerrainGrid:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray

    def __post_init__(self):
        self.x = np.asarray(self.x, dtype=float)
        self.y = np.asarray(self.y, dtype=float)
        self.z = np.asarray(self.z, dtype=float)

        if self.x.shape != self.y.shape or self.x.shape != self.z.shape:
            raise ValueError("x, y et z doivent avoir exactement la même forme.")

        if self.z.ndim != 2:
            raise ValueError("La grille de terrain doit être bidimensionnelle.")

    @property
    def shape(self):
        return self.z.shape

    @property
    def width(self) -> float:
        return float(np.ptp(self.x))

    @property
    def height(self) -> float:
        return float(np.ptp(self.y))

    @property
    def relief(self) -> float:
        return float(np.ptp(self.z))

    @property
    def minimum_elevation(self) -> float:
        return float(np.min(self.z))

    @property
    def maximum_elevation(self) -> float:
        return float(np.max(self.z))

    def copy(self) -> "TerrainGrid":
        return TerrainGrid(
            self.x.copy(),
            self.y.copy(),
            self.z.copy(),
        )

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
