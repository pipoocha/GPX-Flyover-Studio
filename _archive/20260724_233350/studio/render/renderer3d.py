import numpy as np
import pyvista as pv


class Renderer3D:
    def __init__(self, points):
        self.points = points

    def show(self):
        if len(self.points) < 2:
            print("GPX vide")
            return

        lat0 = self.points[0]["lat"]
        lon0 = self.points[0]["lon"]

        pts = []

        for p in self.points:
            x = (p["lon"] - lon0) * 111320 * np.cos(np.radians(lat0))
            y = (p["lat"] - lat0) * 111320
            z = p["ele"]

            pts.append([x, y, z])

        pts = np.array(pts)

        # Création de la polyligne
        poly = pv.PolyData()
        poly.points = pts

        cells = np.concatenate([[len(pts)], np.arange(len(pts))])
        poly.lines = cells

        plotter = pv.Plotter(window_size=(1400, 900))

        plotter.set_background("black")

        plotter.add_mesh(
            poly,
            color="#FC4C02",
            line_width=5,
        )

        plotter.add_axes()
        plotter.show_grid()

        plotter.camera_position = "iso"

        plotter.show(title="GPX Flyover Studio V3")