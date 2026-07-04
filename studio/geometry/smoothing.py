import numpy as np


class ChaikinSmoother:
    def __init__(self, points):
        self.points = np.asarray(points, dtype=float)

    def smooth(self, iterations=2):
        pts = self.points

        if len(pts) < 3:
            return pts

        for _ in range(iterations):
            new_pts = [pts[0]]

            for i in range(len(pts) - 1):
                p0 = pts[i]
                p1 = pts[i + 1]

                q = 0.75 * p0 + 0.25 * p1
                r = 0.25 * p0 + 0.75 * p1

                new_pts.extend([q, r])

            new_pts.append(pts[-1])
            pts = np.asarray(new_pts)

        return pts