from __future__ import annotations

import numpy as np


class TerrainSampler:
    """Échantillonnage bilinéaire du DEM en coordonnées locales."""

    def __init__(self, grid):
        self.grid = grid

        self.x_axis = np.asarray(
            np.mean(grid.x, axis=0),
            dtype=float,
        )
        self.y_axis = np.asarray(
            np.mean(grid.y, axis=1),
            dtype=float,
        )
        self.z = np.asarray(grid.z, dtype=float)

        if self.x_axis[0] > self.x_axis[-1]:
            self.x_axis = self.x_axis[::-1]
            self.z = self.z[:, ::-1]

        if self.y_axis[0] > self.y_axis[-1]:
            self.y_axis = self.y_axis[::-1]
            self.z = self.z[::-1, :]

    @staticmethod
    def _cell(axis, value):
        value = float(value)

        if value <= axis[0]:
            return 0, 0, 0.0

        if value >= axis[-1]:
            last = len(axis) - 1
            return last, last, 0.0

        upper = int(np.searchsorted(axis, value, side="right"))
        lower = upper - 1

        span = axis[upper] - axis[lower]
        fraction = 0.0 if abs(span) < 1e-12 else (
            value - axis[lower]
        ) / span

        return lower, upper, float(fraction)

    def height(self, x, y):
        x0, x1, tx = self._cell(self.x_axis, x)
        y0, y1, ty = self._cell(self.y_axis, y)

        if x0 == x1 and y0 == y1:
            return float(self.z[y0, x0])

        if x0 == x1:
            return float(
                self.z[y0, x0] * (1.0 - ty)
                + self.z[y1, x0] * ty
            )

        if y0 == y1:
            return float(
                self.z[y0, x0] * (1.0 - tx)
                + self.z[y0, x1] * tx
            )

        z00 = self.z[y0, x0]
        z10 = self.z[y0, x1]
        z01 = self.z[y1, x0]
        z11 = self.z[y1, x1]

        bottom = z00 * (1.0 - tx) + z10 * tx
        top = z01 * (1.0 - tx) + z11 * tx

        return float(
            bottom * (1.0 - ty)
            + top * ty
        )

    def alignment_statistics(self, path_coords, expected_offset):
        if len(path_coords) == 0:
            return {
                "mean_error_m": 0.0,
                "max_error_m": 0.0,
            }

        errors = []

        for point in np.asarray(path_coords, dtype=float):
            terrain_z = self.height(point[0], point[1])
            actual_offset = point[2] - terrain_z
            errors.append(
                abs(actual_offset - float(expected_offset))
            )

        return {
            "mean_error_m": float(np.mean(errors)),
            "max_error_m": float(np.max(errors)),
        }
