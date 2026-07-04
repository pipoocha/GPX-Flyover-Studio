import numpy as np
import pyvista as pv


class TubeBuilder:
    def __init__(self, points, radius=8, sides=20):
        self.points = np.asarray(points, dtype=float)
        self.radius = radius
        self.sides = sides

    def build(self):
        pts = self.points

        if len(pts) < 2:
            return pv.PolyData()

        vertices = []
        faces = []

        up = np.array([0.0, 0.0, 1.0])

        for i in range(len(pts)):
            if i == 0:
                tangent = pts[i + 1] - pts[i]
            elif i == len(pts) - 1:
                tangent = pts[i] - pts[i - 1]
            else:
                tangent = pts[i + 1] - pts[i - 1]

            tangent = tangent / max(np.linalg.norm(tangent), 1e-9)

            normal = np.cross(tangent, up)

            if np.linalg.norm(normal) < 1e-6:
                normal = np.array([1.0, 0.0, 0.0])

            normal = normal / np.linalg.norm(normal)
            binormal = np.cross(tangent, normal)
            binormal = binormal / np.linalg.norm(binormal)

            for s in range(self.sides):
                angle = 2 * np.pi * s / self.sides
                offset = (
                    np.cos(angle) * normal * self.radius
                    + np.sin(angle) * binormal * self.radius
                )
                vertices.append(pts[i] + offset)

        for i in range(len(pts) - 1):
            for s in range(self.sides):
                a = i * self.sides + s
                b = i * self.sides + (s + 1) % self.sides
                c = (i + 1) * self.sides + (s + 1) % self.sides
                d = (i + 1) * self.sides + s

                faces.extend([4, a, b, c, d])

        mesh = pv.PolyData(
            np.asarray(vertices),
            np.asarray(faces),
        )

        return mesh