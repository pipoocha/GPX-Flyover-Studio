import numpy as np

import config


class CameraPath:
    def __init__(self, path_coords):
        self.coords = np.asarray(path_coords, dtype=float)

    def ease(self, t):
        return t * t * (3 - 2 * t)

    def smooth_point(self, index, radius):
        start = max(0, index - radius)
        end = min(len(self.coords), index + radius + 1)
        return self.coords[start:end].mean(axis=0)

    def direction_at(self, index):
        max_index = len(self.coords) - 1

        i0 = max(0, index - config.CAMERA_SMOOTHING)
        i1 = min(max_index, index + config.CAMERA_SMOOTHING)

        direction = self.coords[i1] - self.coords[i0]
        direction[2] = 0

        norm = np.linalg.norm(direction)

        if norm < 1:
            return np.array([0.0, 1.0, 0.0])

        return direction / norm

    def camera_at(self, frame_index, total_frames):
        max_index = len(self.coords) - 1

        t = frame_index / max(1, total_frames - 1)
        t = self.ease(t)

        index = int(t * max_index)
        index = max(0, min(index, max_index))

        target_index = min(index + config.LOOK_AHEAD, max_index)

        position_on_path = self.smooth_point(
            index,
            config.CAMERA_SMOOTHING,
        )

        look_target = self.smooth_point(
            target_index,
            config.CAMERA_SMOOTHING,
        )

        direction = self.direction_at(index)

        side = np.array(
            [
                -direction[1],
                direction[0],
                0.0,
            ]
        )

        camera_pos = position_on_path.copy()
        camera_pos -= direction * config.CAMERA_DISTANCE
        camera_pos += side * config.SIDE_OFFSET
        camera_pos[2] = position_on_path[2] + config.CAMERA_HEIGHT

        focal_point = look_target.copy()
        focal_point[2] = look_target[2] + config.FOCAL_HEIGHT

        return tuple(camera_pos), tuple(focal_point), index