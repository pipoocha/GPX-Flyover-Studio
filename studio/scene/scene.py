import pyvista as pv

import config


class Scene:
    def __init__(self, window_size=(1600, 900), off_screen=False):
        self.window_size = (
            max(1, int(window_size[0])),
            max(1, int(window_size[1])),
        )
        self.off_screen = bool(off_screen)
        self.view_angle = float(getattr(config, "CAMERA_VIEW_ANGLE", 30.0))

        self.plotter = pv.Plotter(
            window_size=self.window_size,
            off_screen=self.off_screen,
        )
        # Ciel clair plutôt qu'un fond noir : le terrain se détache comme dans
        # une réalisation cartographique aérienne.
        try:
            self.plotter.set_background("#e6edf1", top="#a8bfce")
        except Exception:
            self.plotter.set_background("#cbdbe4")

        # Anti-crénelage pour les arêtes du relief et surtout la trace.
        try:
            self.plotter.enable_anti_aliasing("ssaa")
        except Exception:
            try:
                self.plotter.enable_anti_aliasing("fxaa")
            except Exception:
                pass

        self.configure_camera()

    def configure_camera(self):
        camera = self.plotter.camera
        camera.parallel_projection = False
        camera.view_angle = self.view_angle

    def synchronize_viewport(self):
        """Aligne le viewport interactif sur la résolution de la vidéo."""
        try:
            self.plotter.window_size = self.window_size
        except Exception:
            pass

        try:
            render_window = self.plotter.render_window
            if render_window is not None:
                render_window.SetSize(*self.window_size)
        except Exception:
            pass

        self.configure_camera()

        try:
            self.plotter.reset_camera_clipping_range()
        except Exception:
            pass

        try:
            self.plotter.renderer.ResetCameraClippingRange()
        except Exception:
            pass

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
        self.configure_camera()

    def show(self):
        self.synchronize_viewport()
        self.plotter.show()
