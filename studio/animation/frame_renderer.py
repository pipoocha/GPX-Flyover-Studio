from pathlib import Path

import config
from studio.scene.track import Track


class FrameRenderer:
    def __init__(self, scene, camera_path, path_coords, output_dir=None):
        self.scene = scene
        self.camera_path = camera_path
        self.path_coords = path_coords
        self.output_dir = Path(output_dir or config.FRAMES_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def clear_frames(self):
        for file in self.output_dir.glob("frame_*.png"):
            file.unlink()

    def render(self, frames=None):
        total_frames = frames or config.TOTAL_FRAMES
        hold_frames = config.FINAL_HOLD_SECONDS * config.FPS
        moving_frames = max(1, total_frames - hold_frames)

        self.clear_frames()

        self.scene.plotter.show(
            auto_close=False,
            interactive=False,
        )

        track_actor = None

        for i in range(total_frames):
            camera_frame = min(i, moving_frames - 1)

            position, focal_point, path_index = self.camera_path.camera_at(
                camera_frame,
                moving_frames,
            )

            self.scene.set_camera(
                position=position,
                focal_point=focal_point,
            )

            if config.TRACE_PROGRESSIVE:
                if i % config.TRACE_UPDATE_EVERY == 0 or i == total_frames - 1:
                    if i >= moving_frames:
                        visible_path = self.path_coords
                    else:
                        visible_path = self.path_coords[: max(2, path_index)]

                    if track_actor is not None:
                        self.scene.plotter.remove_actor(track_actor)

                    track_mesh = Track(
                        visible_path,
                        radius=config.TRACK_RADIUS,
                        sides=config.TRACK_SIDES,
                    ).to_mesh()

                    track_actor = self.scene.add_mesh(
                        track_mesh,
                        color="#FC4C02",
                        smooth_shading=True,
                    )

            self.scene.plotter.reset_camera_clipping_range()
            self.scene.plotter.render()

            file = self.output_dir / f"frame_{i:05d}.png"
            self.scene.plotter.screenshot(str(file))

            if i % 10 == 0 or i == total_frames - 1:
                print(f"Image {i + 1}/{total_frames}")