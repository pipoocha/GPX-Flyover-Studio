import numpy as np


class CatmullRomSpline:
    def __init__(self, points, samples_per_segment=8):
        self.points = np.asarray(points, dtype=float)
        self.samples_per_segment = samples_per_segment

    def interpolate(self):
        pts = self.points

        if len(pts) < 4:
            return pts

        result = []

        for i in range(len(pts) - 1):
            p0 = pts[max(i - 1, 0)]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[min(i + 2, len(pts) - 1)]

            for j in range(self.samples_per_segment):
                t = j / self.samples_per_segment
                t2 = t * t
                t3 = t2 * t

                point = 0.5 * (
                    (2 * p1)
                    + (-p0 + p2) * t
                    + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
                )

                result.append(point)

        result.append(pts[-1])

        return np.asarray(result)