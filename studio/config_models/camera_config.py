from dataclasses import dataclass

import config
from studio.camera.presets import CAMERA_PRESETS


@dataclass
class CameraConfig:
    preset: str = "cinematic"
    height: int = 1700
    distance: int = 3600
    look_ahead: int = 420
    smoothing: int = 45
    focal_height: int = 260
    side_offset: int = 450

    @classmethod
    def from_preset(cls, preset_name):
        preset = CAMERA_PRESETS.get(preset_name)

        if preset is None:
            raise ValueError(
                f"Preset caméra inconnu : {preset_name}. "
                f"Disponibles : {', '.join(CAMERA_PRESETS.keys())}"
            )

        return cls(
            preset=preset_name,
            height=preset["height"],
            distance=preset["distance"],
            look_ahead=preset["look_ahead"],
            smoothing=preset["smoothing"],
            focal_height=preset["focal_height"],
            side_offset=preset["side_offset"],
        )

    def apply(self):
        config.CAMERA_HEIGHT = self.height
        config.CAMERA_DISTANCE = self.distance
        config.LOOK_AHEAD = self.look_ahead
        config.CAMERA_SMOOTHING = self.smoothing
        config.FOCAL_HEIGHT = self.focal_height
        config.SIDE_OFFSET = self.side_offset