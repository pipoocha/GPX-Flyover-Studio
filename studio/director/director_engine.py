import numpy as np

from studio.director.director_camera import DirectorCamera
from studio.director.shot_planner import ShotPlanner
from studio.director.shots import create_shot, smoothstep


class DirectorEngine:
    def __init__(self, path_coords):
        self.coords = np.asarray(path_coords, dtype=float)

        self.base_camera = DirectorCamera(
            self.coords
        )

        self.planner = ShotPlanner()

        self.shots = {
            name: create_shot(name)
            for name in [
                "reveal",
                "follow",
                "helicopter",
                "finish",
            ]
        }

        self.context = {
            "route_center": self.coords.mean(axis=0),
            "route_start": self.coords[0],
            "route_end": self.coords[-1],
            "route_max_z": float(
                self.coords[:, 2].max()
            ),
        }

        self.current_shot_name = None

    @staticmethod
    def blend(a, b, value):
        value = smoothstep(value)

        return (
            np.asarray(a, dtype=float) * (1.0 - value)
            + np.asarray(b, dtype=float) * value
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

    def camera_at_progress(self, progress):
        base_position, base_focal, index = (
            self.base_camera.camera_at_progress(
                progress
            )
        )

        plan = self.planner.plan_at(progress)

        current_name = plan["name"]
        local_progress = plan["local_progress"]

        current_position, current_focal = (
            self.shot_camera(
                shot_name=current_name,
                base_position=base_position,
                base_focal=base_focal,
                local_progress=local_progress,
            )
        )

        previous_name = plan["previous_name"]

        if previous_name is not None:
            previous_position, previous_focal = (
                self.shot_camera(
                    shot_name=previous_name,
                    base_position=base_position,
                    base_focal=base_focal,
                    local_progress=1.0,
                )
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

        if current_name != self.current_shot_name:
            print(f"\nPlan Director : {current_name}")
            self.current_shot_name = current_name

        return current_position, current_focal, index