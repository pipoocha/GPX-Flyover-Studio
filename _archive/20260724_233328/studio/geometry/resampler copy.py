import numpy as np


class PathResampler:
    def __init__(self, points):
        self.points = np.asarray(points, dtype=float)

    def distances(self):
        diffs = np.diff(self.points[:, :2], axis=0)
        seg_lengths = np.linalg.norm(diffs, axis=1)
        return np.insert(np.cumsum(seg_lengths), 0, 0.0)

    def resample(self, spacing=2.0):
        if len(self.points) < 2:
            return self.points

        d = self.distances()
        total = d[-1]

        if total <= 0:
            return self.points

        new_d = np.arange(0, total, spacing)

        new_x = np.interp(new_d, d, self.points[:, 0])
        new_y = np.interp(new_d, d, self.points[:, 1])
        new_z = np.interp(new_d, d, self.points[:, 2])

        return np.column_stack([new_x, new_y, new_z])