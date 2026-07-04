import pyvista as pv


class Scene:
    def __init__(self, window_size=(1600, 900), off_screen=False):
        self.plotter = pv.Plotter(
            window_size=window_size,
            off_screen=off_screen,
        )
        self.plotter.set_background("#111111")

    def add_mesh(self, mesh, **kwargs):
        return self.plotter.add_mesh(mesh, **kwargs)

    def add_light(self, light):
        return self.plotter.add_light(light)

    def add_text(self, text, **kwargs):
        return self.plotter.add_text(text, **kwargs)

    def set_camera(self, position, focal_point, viewup=(0, 0, 1)):
        self.plotter.camera_position = [
            position,
            focal_point,
            viewup,
        ]

    def show(self):
        self.plotter.show()