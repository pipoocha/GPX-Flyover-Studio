from dataclasses import dataclass

import numpy as np


@dataclass
class CameraModifiers:
    height_scale: float = 1.0
    distance_scale: float = 1.0
    focal_height_offset: float = 0.0
    lateral_offset: float = 0.0
    progress_speed: float = 1.0


class EventDirector:
    """
    Transforme les événements du parcours en modifications de caméra.

    Les effets sont progressifs :
    - entrée douce ;
    - intensité maximale au centre de l'événement ;
    - sortie douce.
    """

    EVENT_SETTINGS = {
        "high_point": {
            "window": 0.045,
            "height_scale": 1.30,
            "distance_scale": 1.25,
            "focal_height_offset": 160.0,
            "lateral_offset": 350.0,
            "progress_speed": 0.75,
        },
        "low_point": {
            "window": 0.030,
            "height_scale": 1.08,
            "distance_scale": 1.05,
            "focal_height_offset": 40.0,
            "lateral_offset": 0.0,
            "progress_speed": 0.95,
        },
        "steep_climb": {
            "window": 0.040,
            "height_scale": 1.18,
            "distance_scale": 1.15,
            "focal_height_offset": 110.0,
            "lateral_offset": 180.0,
            "progress_speed": 0.82,
        },
        "steep_descent": {
            "window": 0.040,
            "height_scale": 1.10,
            "distance_scale": 1.18,
            "focal_height_offset": 70.0,
            "lateral_offset": -160.0,
            "progress_speed": 0.88,
        },
    }

    def __init__(self, events):
        self.events = list(events)

        self.active_event_type = None
        self.last_announced_event = None

    @staticmethod
    def clamp(value, minimum=0.0, maximum=1.0):
        return max(
            minimum,
            min(maximum, float(value)),
        )

    @staticmethod
    def smoothstep(value):
        value = EventDirector.clamp(value)

        return (
            value
            * value
            * (3.0 - 2.0 * value)
        )

    def event_strength(
        self,
        progress,
        event,
        window,
    ):
        """
        Renvoie une intensité comprise entre 0 et 1.

        L'intensité vaut :
        - 0 en dehors de la fenêtre ;
        - 1 au centre de l'événement.
        """

        difference = abs(
            float(progress)
            - float(event.progress)
        )

        if difference >= window:
            return 0.0

        normalized = (
            1.0
            - difference / window
        )

        return self.smoothstep(
            normalized
        )

    def modifiers_at(self, progress):
        result = CameraModifiers()

        strongest_event = None
        strongest_strength = 0.0

        for event in self.events:
            settings = self.EVENT_SETTINGS.get(
                event.event_type
            )

            if settings is None:
                continue

            strength = self.event_strength(
                progress=progress,
                event=event,
                window=settings["window"],
            )

            if strength <= 0.0:
                continue

            if strength > strongest_strength:
                strongest_strength = strength
                strongest_event = event

            result.height_scale += (
                settings["height_scale"] - 1.0
            ) * strength

            result.distance_scale += (
                settings["distance_scale"] - 1.0
            ) * strength

            result.focal_height_offset += (
                settings["focal_height_offset"]
                * strength
            )

            result.lateral_offset += (
                settings["lateral_offset"]
                * strength
            )

            result.progress_speed *= (
                1.0
                - (
                    1.0
                    - settings["progress_speed"]
                )
                * strength
            )

        self._announce_event(
            strongest_event,
            strongest_strength,
        )

        return result

    def _announce_event(
        self,
        event,
        strength,
    ):
        if event is None or strength < 0.60:
            self.active_event_type = None
            return

        event_key = (
            event.event_type,
            round(event.progress, 4),
        )

        if event_key == self.last_announced_event:
            return

        labels = {
            "high_point": "POINT HAUT",
            "low_point": "POINT BAS",
            "steep_climb": "FORTE MONTÉE",
            "steep_descent": "FORTE DESCENTE",
        }

        label = labels.get(
            event.event_type,
            event.event_type.upper(),
        )

        print(
            f"\nEvent Director : {label} | "
            f"{event.distance_km:.2f} km | "
            f"{event.altitude:.0f} m"
        )

        self.last_announced_event = event_key
        self.active_event_type = event.event_type

    def apply(
        self,
        position,
        focal_point,
        progress,
    ):
        position = np.asarray(
            position,
            dtype=float,
        ).copy()

        focal_point = np.asarray(
            focal_point,
            dtype=float,
        ).copy()

        modifiers = self.modifiers_at(
            progress
        )

        view_vector = (
            position - focal_point
        )

        horizontal_vector = (
            view_vector.copy()
        )

        horizontal_vector[2] = 0.0

        horizontal_norm = np.linalg.norm(
            horizontal_vector
        )

        if horizontal_norm < 1e-9:
            direction = np.array(
                [0.0, -1.0, 0.0],
                dtype=float,
            )
        else:
            direction = (
                horizontal_vector
                / horizontal_norm
            )

        side = np.array(
            [
                -direction[1],
                direction[0],
                0.0,
            ],
            dtype=float,
        )

        new_position = (
            focal_point
            + view_vector
            * modifiers.distance_scale
        )

        original_height_difference = (
            position[2]
            - focal_point[2]
        )

        new_position[2] = (
            focal_point[2]
            + original_height_difference
            * modifiers.height_scale
        )

        new_position += (
            side
            * modifiers.lateral_offset
        )

        new_focal = focal_point.copy()

        new_focal[2] += (
            modifiers.focal_height_offset
        )

        return (
            new_position,
            new_focal,
            modifiers,
        )