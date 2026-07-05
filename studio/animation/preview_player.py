import time

import config


class PreviewPlayer:
    def __init__(self, scene, camera_path, frames=300):
        self.scene = scene
        self.camera_path = camera_path
        self.frames = frames

    def play(self):
        print("PREVIEW animé : aucune vidéo générée.")
        print("Ferme la fenêtre PyVista pour terminer.")

        self.scene.plotter.show(
            auto_close=False,
            interactive_update=True,
        )

        for i in range(self.frames):
            progress = i / max(1, self.frames - 1)

            position, focal_point, _ = self.camera_path.camera_at_progress(
                progress
            )

            self.scene.set_camera(
                position=position,
                focal_point=focal_point,
            )

            self.scene.plotter.reset_camera_clipping_range()
            self.scene.plotter.update()

            time.sleep(1 / max(1, config.FPS))

        self.scene.plotter.show()