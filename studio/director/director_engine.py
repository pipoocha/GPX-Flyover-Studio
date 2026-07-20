import numpy as np

from studio.director.director_camera import DirectorCamera
from studio.director.route_event_analyzer import (
    RouteEventAnalyzer,
)
from studio.director.shot_planner import ShotPlanner
from studio.director.shots import (
    create_shot,
    smoothstep,
)


class DirectorEngine:
    def __init__(self, path_coords):
        self.coords = np.asarray(
            path_coords,
            dtype=float,
        )

        self.base_camera = DirectorCamera(
            self.coords
        )

        self.planner = ShotPlanner()

        self.shots = {
            name: create_shot(name)
            for name in (
                "reveal",
                "follow",
                "helicopter",
                "finish",
            )
        }

        self.context = {
            "route_center": self.coords.mean(
                axis=0
            ),
            "route_start": self.coords[0],
            "route_end": self.coords[-1],
            "route_max_z": float(
                self.coords[:, 2].max()
            ),
        }

        self.current_shot_name = None
        self.last_event_index = -1

        self.event_analyzer = RouteEventAnalyzer(
            self.coords,
            smoothing_window=41,
            prominence_threshold=20.0,
            minimum_spacing_m=300.0,
            steep_slope_threshold=0.08,
        )

        self.events = (
            self.event_analyzer.analyze()
        )

        self.print_events()

    def print_events(self):
        print()
        print(
            "Événements du parcours détectés :",
            len(self.events),
        )

        for event in self.events:
            label = {
                "high_point": "point haut",
                "low_point": "point bas",
                "steep_climb": "forte montée",
                "steep_descent": "forte descente",
            }.get(
                event.event_type,
                event.event_type,
            )

            print(
                f"  - {label:15s} | "
                f"{event.distance_km:6.2f} km | "
                f"{event.altitude:7.0f} m | "
                f"{event.progress * 100:5.1f} %"
            )

        print()

    @staticmethod
    def blend(a, b, value):
        value = smoothstep(value)

        return (
            np.asarray(a, dtype=float)
            * (1.0 - value)
            + np.asarray(b, dtype=float)
            * value
        )

    def event_at_progress(
        self,
        progress,
        tolerance=0.008,
    ):
        for index, event in enumerate(
            self.events
        ):
            if index <= self.last_event_index:
                continue

            difference = abs(
                progress - event.progress
            )

            if difference <= tolerance:
                self.last_event_index = index
                return event

        return None

    def print_event_reached(
        self,
        event,
    ):
        label = {
            "high_point": "POINT HAUT",
            "low_point": "POINT BAS",
            "steep_climb": "FORTE MONTÉE",
            "steep_descent": "FORTE DESCENTE",
        }.get(
            event.event_type,
            event.event_type.upper(),
        )

        print(
            f"\nÉvénement Director : {label} | "
            f"{event.distance_km:.2f} km | "
            f"{event.altitude:.0f} m"
        )

    def shot_camera(
        self,
        shot_name,
        base_position,
        base_focal,
        local_progress,
    ):
        shot = self.shots[shot_name]

        return shot.apply(
            position=base_position,
            focal_point=base_focal,
            local_progress=local_progress,
            context=self.context,
        )

    def camera_at_progress(
        self,
        progress,
    ):
        (
            base_position,
            base_focal,
            index,
        ) = self.base_camera.camera_at_progress(
            progress
        )

        event = self.event_at_progress(
            progress
        )

        if event is not None:
            self.print_event_reached(
                event
            )

        plan = self.planner.plan_at(
            progress
        )

        current_name = plan["name"]

        current_position, current_focal = (
            self.shot_camera(
                shot_name=current_name,
                base_position=base_position,
                base_focal=base_focal,
                local_progress=plan[
                    "local_progress"
                ],
            )
        )

        previous_name = plan[
            "previous_name"
        ]

        if previous_name is not None:
            (
                previous_position,
                previous_focal,
            ) = self.shot_camera(
                shot_name=previous_name,
                base_position=base_position,
                base_focal=base_focal,
                local_progress=1.0,
            )

            current_position = self.blend(
                previous_position,
                current_position,
                plan["transition"],
            )

            current_focal = self.blend(
                previous_focal,
                current_focal,
                plan["transition"],
            )

        if (
            current_name
            != self.current_shot_name
        ):
            print(
                f"\nPlan Director : "
                f"{current_name}"
            )

            self.current_shot_name = (
                current_name
            )

        return (
            current_position,
            current_focal,
            index,
        )