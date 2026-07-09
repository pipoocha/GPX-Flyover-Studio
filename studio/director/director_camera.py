import numpy as np

import config
from studio.director.orientation import OrientationController


class DirectorCamera:
    def __init__(self, path_coords):
        self.coords = np.asarray(path_coords, dtype=float)

        self.center = self.coords.mean(axis=0)

        xy = self.coords[:, :2]
        self.min_xy = xy.min(axis=0)
        self.max_xy = xy.max(axis=0)

        self.size = max(self.max_xy - self.min_xy)
        self.max_z = self.coords[:, 2].max()

        orientation_mode = getattr(config, "CAMERA_ORIENTATION_MODE", "route")
        orientation_angle = getattr(config, "CAMERA_ORIENTATION_ANGLE", 0)

        self.orientation = OrientationController(
            self.coords,
            mode=orientation_mode,
            angle=orientation_angle,
        )

        self.global_direction = self.orientation.direction()

        self.side = np.array(
            [
                -self.global_direction[1],
                self.global_direction[0],
                0.0,
            ]
        )

    def point_at(self, progress):
        progress = max(0.0, min(1.0, progress))

        index = int(progress * (len(self.coords) - 1))
        index = max(0, min(index, len(self.coords) - 1))

        return self.coords[index], index

    def camera_at_progress(self, progress):
        active, index = self.point_at(progress)

        look_index = min(
            index + config.LOOK_AHEAD,
            len(self.coords) - 1,
        )

        look = self.coords[look_index]

        moving_center = self.center * 0.65 + active * 0.35

        height = max(
            config.CAMERA_HEIGHT,
            self.size * 0.45,
        )

        distance = max(
            config.CAMERA_DISTANCE,
            self.size * 0.95,
        )

        camera_pos = moving_center.copy()
        camera_pos -= self.global_direction * distance
        camera_pos += self.side * config.SIDE_OFFSET
        camera_pos[2] = self.max_z + height

        focal_point = active * 0.65 + look * 0.35
        focal_point[2] += config.FOCAL_HEIGHT

        return camera_pos, focal_point, index