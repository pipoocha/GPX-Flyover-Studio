import time

import config


class PreviewPlayer:
    """
    Prévisualisation animée dans une fenêtre PyVista.

    Aucun fichier image et aucune vidéo ne sont générés.
    Les informations de progression sont affichées dans la console.
    """

    def __init__(
        self,
        scene,
        camera_path,
        frames=300,
        fps=None,
    ):
        self.scene = scene
        self.camera_path = camera_path
        self.frames = max(2, int(frames))
        self.fps = max(1, int(fps or config.FPS))

    def print_header(self):
        camera_mode = getattr(config, "CAMERA_MODE", "flyover")
        orientation_mode = getattr(
            config,
            "CAMERA_ORIENTATION_MODE",
            "route",
        )

        print()
        print("===================================")
        print("PREVIEW DIRECTOR")
        print("Aucune vidéo ne sera générée")
        print("-----------------------------------")
        print("Caméra      :", camera_mode)
        print("Orientation :", orientation_mode)
        print("Preset      :", self.camera_preset_name())
        print("Images      :", self.frames)
        print("FPS preview :", self.fps)
        print("Durée       :", f"{self.frames / self.fps:.1f} s")
        print("===================================")
        print()

    @staticmethod
    def camera_preset_name():
        timeline = getattr(config, "TIMELINE", [])

        if timeline:
            return "timeline"

        return getattr(
            config,
            "CAMERA_PRESET",
            "paramètres du projet",
        )

    def print_progress(self, frame_index, progress):
        percentage = progress * 100.0

        print(
            f"\rPreview : "
            f"{frame_index + 1:4d}/{self.frames} | "
            f"{percentage:6.1f} % | "
            f"caméra={getattr(config, 'CAMERA_MODE', 'flyover')} | "
            f"orientation="
            f"{getattr(config, 'CAMERA_ORIENTATION_MODE', 'route')}",
            end="",
            flush=True,
        )

    def play(self):
        self.print_header()

        plotter = self.scene.plotter

        plotter.show(
            auto_close=False,
            interactive_update=True,
        )

        frame_duration = 1.0 / self.fps

        for frame_index in range(self.frames):
            frame_start = time.perf_counter()

            progress = frame_index / max(1, self.frames - 1)

            position, focal_point, _ = (
                self.camera_path.camera_at_progress(progress)
            )

            self.scene.set_camera(
                position=tuple(position),
                focal_point=tuple(focal_point),
            )

            plotter.reset_camera_clipping_range()
            plotter.render()
            plotter.update()

            if (
                frame_index % max(1, self.fps // 2) == 0
                or frame_index == self.frames - 1
            ):
                self.print_progress(
                    frame_index=frame_index,
                    progress=progress,
                )

            elapsed = time.perf_counter() - frame_start
            remaining = frame_duration - elapsed

            if remaining > 0:
                time.sleep(remaining)

        print()
        print()
        print("Preview terminée.")
        print("La fenêtre reste ouverte.")
        print("Ferme-la pour revenir à PowerShell.")

        plotter.show()