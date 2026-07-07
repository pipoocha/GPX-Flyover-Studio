import numpy as np

import config


class CameraPath:
    def __init__(self, path_coords):
        self.coords = np.asarray(path_coords, dtype=float)

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

    def camera_at_progress(self, progress):
        max_index = len(self.coords) - 1

        progress = max(0.0, min(1.0, progress))

        index = int(progress * max_index)
        index = max(0, min(index, max_index))

        target_index = min(index + config.LOOK_AHEAD, max_index)

        p = self.smooth_point(index, config.CAMERA_SMOOTHING)
        target = self.smooth_point(target_index, config.CAMERA_SMOOTHING)

        direction = self.direction_at(index)
        side = np.array([-direction[1], direction[0], 0.0])

        camera_pos = p.copy()
        camera_pos -= direction * config.CAMERA_DISTANCE
        camera_pos += side * config.SIDE_OFFSET
        camera_pos[2] = p[2] + config.CAMERA_HEIGHT

        focal_point = target.copy()
        focal_point[2] = target[2] + config.FOCAL_HEIGHT

        return camera_pos, focal_point, index