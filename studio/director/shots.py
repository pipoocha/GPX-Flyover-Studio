import numpy as np

import config


def smoothstep(value):
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


class BaseShot:
    name = "base"

    def apply(self, position, focal_point, local_progress, context):
        return (
            np.asarray(position, dtype=float),
            np.asarray(focal_point, dtype=float),
        )


class RevealShot(BaseShot):
    name = "reveal"

    def apply(self, position, focal_point, local_progress, context):
        position = np.asarray(position, dtype=float)
        focal_point = np.asarray(focal_point, dtype=float)
        t = smoothstep(local_progress)

        # Plan large au départ, mais toujours centré sur la portion locale de
        # l'itinéraire. L'ancienne version visait le centre GLOBAL du parcours,
        # ce qui pouvait placer la trace hors écran dès les premières secondes.
        view_vector = position - focal_point
        distance_factor = 1.38 - 0.38 * t
        new_position = focal_point + view_vector * distance_factor
        new_position[2] += (1.0 - t) * float(getattr(config, "CAMERA_HEIGHT", 1400.0)) * 0.22
        return new_position, focal_point.copy()


class FollowShot(BaseShot):
    name = "follow"


class HelicopterShot(BaseShot):
    name = "helicopter"

    def apply(self, position, focal_point, local_progress, context):
        position = np.asarray(position, dtype=float)
        focal_point = np.asarray(focal_point, dtype=float)

        direction = focal_point - position
        direction[2] = 0.0
        norm = np.linalg.norm(direction)
        if norm < 1e-6:
            side = np.array([1.0, 0.0, 0.0])
        else:
            direction /= norm
            side = np.array([-direction[1], direction[0], 0.0])

        t = smoothstep(local_progress)
        # Le plan hélicoptère reste perceptible mais ne doit plus pousser la
        # trajectoire jusqu'au bord de l'image.
        base_side = float(getattr(config, "SIDE_OFFSET", 450.0))
        lateral_offset = base_side * (0.28 + 0.10 * t)
        vertical_offset = float(getattr(config, "CAMERA_HEIGHT", 1400.0)) * 0.08

        new_position = position.copy()
        new_position += side * lateral_offset
        new_position[2] += vertical_offset
        return new_position, focal_point.copy()


class FinishShot(BaseShot):
    name = "finish"

    def apply(self, position, focal_point, local_progress, context):
        position = np.asarray(position, dtype=float)
        focal_point = np.asarray(focal_point, dtype=float)
        t = smoothstep(local_progress)

        # Élargissement progressif sans regarder vers le centre global du GPX.
        view_vector = position - focal_point
        distance_factor = 1.0 + 0.34 * t
        new_position = focal_point + view_vector * distance_factor
        new_position[2] += float(getattr(config, "CAMERA_HEIGHT", 1400.0)) * 0.18 * t
        return new_position, focal_point.copy()


SHOT_TYPES = {
    "reveal": RevealShot,
    "follow": FollowShot,
    "helicopter": HelicopterShot,
    "finish": FinishShot,
}


def create_shot(name):
    shot_class = SHOT_TYPES.get(str(name).lower())
    if shot_class is None:
        raise ValueError(
            f"Plan inconnu : {name}. "
            f"Disponibles : {', '.join(SHOT_TYPES)}"
        )
    return shot_class()
