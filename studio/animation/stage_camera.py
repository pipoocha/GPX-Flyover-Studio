import numpy as np

import config


class StageCamera:
    """
    Caméra type présentation d'étape :
    - relief plus stable ;
    - rotation limitée ;
    - caméra haute ;
    - trace toujours visible ;
    - regard vers la partie active de la trace.
    """

    def __init__(self, path_coords):
        self.coords = np.asarray(path_coords, dtype=float)

        self.center = self.coords.mean(axis=0)

        xy = self.coords[:, :2]
        self.min_xy = xy.min(axis=0)
        self.max_xy = xy.max(axis=0)

        size_xy = self.max_xy - self.min_xy
        self.size = max(size_xy[0], size_xy[1])

        self.base_height = max(config.CAMERA_HEIGHT, self.size * 0.55)
        self.base_distance = max(config.CAMERA_DISTANCE, self.size * 1.10)

    def camera_at_progress(self, progress):
        max_index = len(self.coords) - 1

        progress = max(0.0, min(1.0, progress))
        index = int(progress * max_index)
        index = max(0, min(index, max_index))

        # Point actif de la trace
        active = self.coords[index]

        # Point regardé : un peu devant la progression
        look_index = min(index + config.LOOK_AHEAD, max_index)
        look_point = self.coords[look_index]

        # Direction générale FIXE du parcours, pour éviter que le fond tourne sans arrêt
        start = self.coords[0]
        end = self.coords[-1]

        direction = end - start
        direction[2] = 0

        norm = np.linalg.norm(direction)

        if norm < 1:
            direction = np.array([0.0, 1.0, 0.0])
        else:
            direction = direction / norm

        side = np.array([-direction[1], direction[0], 0.0])

        # La caméra se déplace doucement vers le point actif,
        # mais reste orientée dans une direction générale stable.
        camera_center = (
            self.center * 0.55
            + active * 0.45
        )

        camera_pos = camera_center.copy()
        camera_pos -= direction * self.base_distance
        camera_pos += side * config.SIDE_OFFSET
        camera_pos[2] = max(
            active[2] + self.base_height,
            self.coords[:, 2].max() + config.CAMERA_HEIGHT * 0.35,
        )

        focal_point = (
            active * 0.65
            + look_point * 0.35
        )
        focal_point[2] += config.FOCAL_HEIGHT

        return camera_pos, focal_point, index