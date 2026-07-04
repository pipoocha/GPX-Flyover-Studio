import os
from pathlib import Path

import imageio.v2 as imageio

import config


class VideoExporter:
    def __init__(self, frames_dir=None, output_file=None, fps=None):
        self.frames_dir = Path(frames_dir or config.FRAMES_DIR)
        self.output_file = Path(output_file or config.DEFAULT_VIDEO)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.fps = fps or config.FPS

    def export(self):
        frames = sorted(self.frames_dir.glob("frame_*.png"))

        print(f"Images trouvées : {len(frames)}")

        if not frames:
            raise RuntimeError(f"Aucune image trouvée dans {self.frames_dir}")

        temp_file = self.output_file.with_name("flyover_temp.mp4")

        if temp_file.exists():
            temp_file.unlink()

        with imageio.get_writer(
            str(temp_file),
            fps=self.fps,
            codec="libx264",
            quality=8,
            macro_block_size=16,
        ) as writer:
            total = len(frames)

            for i, frame in enumerate(frames):
                writer.append_data(imageio.imread(frame))

                if i % 10 == 0 or i == total - 1:
                    print(f"Vidéo : {i + 1}/{total}")

        try:
            os.replace(temp_file, self.output_file)
        except PermissionError:
            raise RuntimeError(
                "Impossible d'écraser la vidéo. Ferme VLC ou le lecteur vidéo."
            )

        print("Vidéo créée :")
        print(self.output_file.resolve())