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

        view_vector = position - focal_point
        distance_factor = 1.8 - 0.8 * t

        new_position = focal_point + view_vector * distance_factor
        new_position[2] += (1.0 - t) * config.CAMERA_HEIGHT * 0.8

        route_center = context["route_center"]

        new_focal = (
            route_center * (1.0 - t)
            + focal_point * t
        )

        return new_position, new_focal


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
            side = np.array(
                [-direction[1], direction[0], 0.0]
            )

        t = smoothstep(local_progress)

        lateral_offset = config.SIDE_OFFSET * (1.2 + 0.3 * t)
        vertical_offset = config.CAMERA_HEIGHT * 0.25

        new_position = position.copy()
        new_position += side * lateral_offset
        new_position[2] += vertical_offset

        return new_position, focal_point


class FinishShot(BaseShot):
    name = "finish"

    def apply(self, position, focal_point, local_progress, context):
        position = np.asarray(position, dtype=float)
        focal_point = np.asarray(focal_point, dtype=float)

        t = smoothstep(local_progress)

        route_center = context["route_center"]
        view_vector = position - focal_point

        distance_factor = 1.0 + 0.9 * t

        new_position = focal_point + view_vector * distance_factor
        new_position[2] += config.CAMERA_HEIGHT * 0.9 * t

        new_focal = (
            focal_point * (1.0 - t)
            + route_center * t
        )

        return new_position, new_focal


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