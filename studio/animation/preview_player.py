import time

import config


class PreviewPlayer:
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

        self.paused = False
        self.stopped = False
        self.frame_index = 0

    def toggle_pause(self):
        self.paused = not self.paused

        if self.paused:
            print("\nPreview en pause.")
        else:
            print("\nPreview reprise.")

    def stop(self):
        self.stopped = True
        print("\nArrêt du preview demandé.")

    def print_header(self):
        print()
        print("===================================")
        print("PREVIEW DIRECTOR")
        print("Aucune vidéo ne sera générée")
        print("-----------------------------------")
        print("Caméra      :", getattr(config, "CAMERA_MODE", "flyover"))
        print(
            "Orientation :",
            getattr(config, "CAMERA_ORIENTATION_MODE", "route"),
        )
        print(
            "Preset      :",
            getattr(config, "CAMERA_PRESET", "cinematic"),
        )
        print("Images      :", self.frames)
        print("FPS preview :", self.fps)
        print("Durée       :", f"{self.frames / self.fps:.1f} s")
        print("-----------------------------------")
        print("Espace : pause / reprise")
        print("Q      : arrêter le preview")
        print("===================================")
        print()

    def print_progress(self, progress):
        print(
            f"\rPreview : "
            f"{self.frame_index + 1:4d}/{self.frames} | "
            f"{progress * 100:6.1f} % | "
            f"caméra={getattr(config, 'CAMERA_MODE', 'flyover')} | "
            f"orientation="
            f"{getattr(config, 'CAMERA_ORIENTATION_MODE', 'route')} | "
            f"preset={getattr(config, 'CAMERA_PRESET', 'cinematic')}",
            end="",
            flush=True,
        )

    def play(self):
        self.print_header()

        plotter = self.scene.plotter

        plotter.add_key_event(
            "space",
            self.toggle_pause,
        )

        plotter.add_key_event(
            "q",
            self.stop,
        )

        plotter.show(
            auto_close=False,
            interactive_update=True,
        )

        frame_duration = 1.0 / self.fps

        while self.frame_index < self.frames and not self.stopped:
            frame_start = time.perf_counter()

            plotter.update()

            if self.paused:
                time.sleep(0.03)
                continue

            progress = self.frame_index / max(1, self.frames - 1)

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
                self.frame_index % max(1, self.fps // 2) == 0
                or self.frame_index == self.frames - 1
            ):
                self.print_progress(progress)

            self.frame_index += 1

            elapsed = time.perf_counter() - frame_start
            remaining = frame_duration - elapsed

            if remaining > 0:
                time.sleep(remaining)

        print()

        if self.stopped:
            print("Preview arrêtée.")
        else:
            print("Preview terminée.")

        print("La fenêtre reste ouverte.")
        print("Ferme-la pour revenir à PowerShell.")

        plotter.show()