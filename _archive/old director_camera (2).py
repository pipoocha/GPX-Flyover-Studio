import numpy as np

import config
from studio.director.orientation import OrientationController


class DirectorCamera:
    """
    Caméra prédictive :

    - anticipe les virages ;
    - regarde plus loin dans les portions droites ;
    - prend de la hauteur dans les fortes montées ;
    - ouvre le cadrage lorsque le relief devient important ;
    - conserve l'orientation north / route / fixed / auto.
    """

    def __init__(self, path_coords):
        self.coords = np.asarray(
            path_coords,
            dtype=float,
        )

        if len(self.coords) < 2:
            raise ValueError(
                "La trajectoire doit contenir au moins deux points."
            )

        self.center = self.coords.mean(axis=0)

        xy = self.coords[:, :2]

        self.min_xy = xy.min(axis=0)
        self.max_xy = xy.max(axis=0)

        extent = self.max_xy - self.min_xy

        self.size = float(
            max(
                extent[0],
                extent[1],
                1.0,
            )
        )

        self.min_z = float(
            self.coords[:, 2].min()
        )

        self.max_z = float(
            self.coords[:, 2].max()
        )

        self.relief_range = max(
            1.0,
            self.max_z - self.min_z,
        )

        orientation_mode = getattr(
            config,
            "CAMERA_ORIENTATION_MODE",
            "route",
        )

        orientation_angle = getattr(
            config,
            "CAMERA_ORIENTATION_ANGLE",
            0.0,
        )

        self.orientation = OrientationController(
            self.coords,
            mode=orientation_mode,
            angle=orientation_angle,
        )

        self.base_look_ahead = max(
            2,
            int(
                getattr(
                    config,
                    "LOOK_AHEAD",
                    420,
                )
            ),
        )

        self.predictive_enabled = bool(
            getattr(
                config,
                "PREDICTIVE_CAMERA_ENABLED",
                True,
            )
        )

        self.minimum_look_ahead = max(
            2,
            int(
                getattr(
                    config,
                    "PREDICTIVE_MIN_LOOK_AHEAD",
                    max(
                        20,
                        self.base_look_ahead // 3,
                    ),
                )
            ),
        )

        self.maximum_look_ahead = max(
            self.minimum_look_ahead,
            int(
                getattr(
                    config,
                    "PREDICTIVE_MAX_LOOK_AHEAD",
                    self.base_look_ahead * 2,
                )
            ),
        )

        self.analysis_window = max(
            3,
            int(
                getattr(
                    config,
                    "PREDICTIVE_ANALYSIS_WINDOW",
                    max(
                        15,
                        self.base_look_ahead // 4,
                    ),
                )
            ),
        )

        self.curvature_strength = float(
            getattr(
                config,
                "PREDICTIVE_CURVATURE_STRENGTH",
                0.75,
            )
        )

        self.slope_strength = float(
            getattr(
                config,
                "PREDICTIVE_SLOPE_STRENGTH",
                1.0,
            )
        )

        self.relief_strength = float(
            getattr(
                config,
                "PREDICTIVE_RELIEF_STRENGTH",
                0.65,
            )
        )

        self.focal_smoothing = float(
            getattr(
                config,
                "PREDICTIVE_FOCAL_SMOOTHING",
                0.10,
            )
        )

        self.position_smoothing = float(
            getattr(
                config,
                "PREDICTIVE_POSITION_SMOOTHING",
                0.08,
            )
        )

        self.previous_position = None
        self.previous_focal = None
        self.previous_look_ahead = float(
            self.base_look_ahead
        )

        # Inertie de caméra type drone.
        self.spring = float(
            getattr(
                config,
                "CAMERA_SPRING",
                0.12,
            )
        )

        self.damping = float(
            getattr(
                config,
                "CAMERA_DAMPING",
                0.82,
            )
        )

        self.velocity_position = np.zeros(
            3,
            dtype=float,
        )

        self.velocity_focal = np.zeros(
            3,
            dtype=float,
        )

    @staticmethod
    def clamp(value, minimum, maximum):
        return max(
            minimum,
            min(maximum, value),
        )

    @staticmethod
    def normalize(vector):
        vector = np.asarray(
            vector,
            dtype=float,
        )

        norm = np.linalg.norm(vector)

        if norm < 1e-9:
            return np.array(
                [0.0, 1.0, 0.0],
                dtype=float,
            )

        return vector / norm

    def index_at_progress(self, progress):
        progress = self.clamp(
            float(progress),
            0.0,
            1.0,
        )

        index = int(
            progress
            * (len(self.coords) - 1)
        )

        return max(
            0,
            min(
                index,
                len(self.coords) - 1,
            ),
        )

    def point_at(self, progress):
        index = self.index_at_progress(
            progress
        )

        return self.coords[index], index

    def direction_between(
        self,
        index_0,
        index_1,
    ):
        index_0 = max(
            0,
            min(index_0, len(self.coords) - 1),
        )

        index_1 = max(
            0,
            min(index_1, len(self.coords) - 1),
        )

        direction = (
            self.coords[index_1]
            - self.coords[index_0]
        )

        direction[2] = 0.0

        return self.normalize(direction)

    def curvature_at(self, index):
        """
        Renvoie une courbure comprise approximativement entre 0 et 1.

        0 = portion droite
        1 = virage très marqué
        """

        window = self.analysis_window

        previous_index = max(
            0,
            index - window,
        )

        next_index = min(
            len(self.coords) - 1,
            index + window,
        )

        direction_before = self.direction_between(
            previous_index,
            index,
        )

        direction_after = self.direction_between(
            index,
            next_index,
        )

        dot_value = float(
            np.dot(
                direction_before,
                direction_after,
            )
        )

        dot_value = self.clamp(
            dot_value,
            -1.0,
            1.0,
        )

        angle = float(
            np.arccos(dot_value)
        )

        return self.clamp(
            angle / np.pi,
            0.0,
            1.0,
        )

    def slope_at(self, index):
        """
        Calcule une pente locale normalisée.

        Valeur positive : montée.
        Valeur négative : descente.
        """

        window = self.analysis_window

        index_0 = max(
            0,
            index - window,
        )

        index_1 = min(
            len(self.coords) - 1,
            index + window,
        )

        point_0 = self.coords[index_0]
        point_1 = self.coords[index_1]

        horizontal_distance = np.linalg.norm(
            point_1[:2] - point_0[:2]
        )

        if horizontal_distance < 1e-6:
            return 0.0

        slope = (
            point_1[2] - point_0[2]
        ) / horizontal_distance

        return self.clamp(
            float(slope),
            -1.0,
            1.0,
        )

    def relief_ahead(self, index):
        """
        Analyse l'amplitude verticale devant la progression.
        """

        end_index = min(
            len(self.coords),
            index
            + self.maximum_look_ahead
            + 1,
        )

        points = self.coords[
            index:end_index
        ]

        if len(points) < 2:
            return 0.0

        local_range = float(
            points[:, 2].max()
            - points[:, 2].min()
        )

        return self.clamp(
            local_range
            / self.relief_range,
            0.0,
            1.0,
        )

    def predictive_look_ahead(
        self,
        index,
    ):
        if not self.predictive_enabled:
            return self.base_look_ahead

        curvature = self.curvature_at(
            index
        )

        slope = abs(
            self.slope_at(index)
        )

        relief = self.relief_ahead(
            index
        )

        # Ligne droite : regard plus loin.
        straight_factor = (
            1.0
            - curvature
            * self.curvature_strength
        )

        # Relief marqué : anticipation légèrement accrue.
        terrain_factor = (
            1.0
            + relief
            * self.relief_strength
            * 0.35
        )

        # Forte pente : réduction modérée pour ne pas viser trop loin.
        slope_factor = (
            1.0
            - slope
            * self.slope_strength
            * 0.30
        )

        raw_look_ahead = (
            self.base_look_ahead
            * straight_factor
            * terrain_factor
            * slope_factor
        )

        raw_look_ahead = self.clamp(
            raw_look_ahead,
            self.minimum_look_ahead,
            self.maximum_look_ahead,
        )

        # Empêche le changement brutal de distance de regard.
        alpha = 0.08

        smoothed = (
            self.previous_look_ahead
            * (1.0 - alpha)
            + raw_look_ahead
            * alpha
        )

        self.previous_look_ahead = smoothed

        return int(round(smoothed))

    def adaptive_height(
        self,
        index,
    ):
        base_height = max(
            float(config.CAMERA_HEIGHT),
            self.size * 0.45,
        )

        if not self.predictive_enabled:
            return base_height

        slope = self.slope_at(
            index
        )

        relief = self.relief_ahead(
            index
        )

        climbing_factor = max(
            0.0,
            slope,
        )

        additional_height = (
            base_height
            * (
                relief
                * self.relief_strength
                * 0.35
                + climbing_factor
                * self.slope_strength
                * 0.30
            )
        )

        return (
            base_height
            + additional_height
        )

    def adaptive_distance(
        self,
        index,
    ):
        base_distance = max(
            float(config.CAMERA_DISTANCE),
            self.size * 0.95,
        )

        if not self.predictive_enabled:
            return base_distance

        curvature = self.curvature_at(
            index
        )

        relief = self.relief_ahead(
            index
        )

        # Virage important : caméra légèrement plus proche.
        curve_factor = (
            1.0
            - curvature
            * self.curvature_strength
            * 0.18
        )

        # Relief important : caméra plus éloignée pour ouvrir le champ.
        relief_factor = (
            1.0
            + relief
            * self.relief_strength
            * 0.25
        )

        return (
            base_distance
            * curve_factor
            * relief_factor
        )

    def smooth_vector(
        self,
        previous,
        target,
        alpha,
    ):
        target = np.asarray(
            target,
            dtype=float,
        )

        if previous is None:
            return target.copy()

        return (
            np.asarray(previous, dtype=float)
            * (1.0 - alpha)
            + target
            * alpha
        )

    def inertial_filter(
        self,
        current,
        target,
        velocity,
    ):
        """
        Filtre ressort amorti.

        Il donne à la caméra une sensation de masse :
        elle accélère et ralentit progressivement au lieu
        de suivre instantanément la cible calculée.
        """

        current = np.asarray(
            current,
            dtype=float,
        )

        target = np.asarray(
            target,
            dtype=float,
        )

        velocity = np.asarray(
            velocity,
            dtype=float,
        )

        force = (
            target - current
        ) * self.spring

        velocity = (
            velocity * self.damping
            + force
        )

        current = (
            current + velocity
        )

        return current, velocity

    def camera_at_progress(
        self,
        progress,
    ):
        active, index = self.point_at(
            progress
        )

        look_ahead = (
            self.predictive_look_ahead(
                index
            )
        )

        look_index = min(
            index + look_ahead,
            len(self.coords) - 1,
        )

        # Point intermédiaire pour anticiper le virage sans viser
        # brutalement le point lointain.
        middle_index = min(
            index
            + max(1, look_ahead // 2),
            len(self.coords) - 1,
        )

        middle_point = self.coords[
            middle_index
        ]

        look_point = self.coords[
            look_index
        ]

        direction = (
            self.orientation
            .direction_at_progress(
                progress
            )
        )

        direction = self.normalize(
            direction
        )

        side = np.array(
            [
                -direction[1],
                direction[0],
                0.0,
            ],
            dtype=float,
        )

        moving_center = (
            self.center * 0.55
            + active * 0.45
        )

        camera_height = (
            self.adaptive_height(
                index
            )
        )

        camera_distance = (
            self.adaptive_distance(
                index
            )
        )

        camera_position = (
            moving_center.copy()
        )

        camera_position -= (
            direction
            * camera_distance
        )

        camera_position += (
            side
            * float(config.SIDE_OFFSET)
        )

        camera_position[2] = max(
            active[2] + camera_height,
            self.max_z
            + camera_height
            * 0.35,
        )

        slope = self.slope_at(
            index
        )

        relief = self.relief_ahead(
            index
        )

        # Mélange du point actif, du milieu et du point anticipé.
        focal_point = (
            active * 0.25
            + middle_point * 0.35
            + look_point * 0.40
        )

        # En montée ou dans un relief important, vise plus haut.
        focal_point[2] += (
            float(config.FOCAL_HEIGHT)
            + max(0.0, slope)
            * camera_height
            * 0.15
            + relief
            * camera_height
            * 0.08
        )

        if self.previous_position is None:
            self.previous_position = (
                camera_position.copy()
            )

        if self.previous_focal is None:
            self.previous_focal = (
                focal_point.copy()
            )

        (
            camera_position,
            self.velocity_position,
        ) = self.inertial_filter(
            current=self.previous_position,
            target=camera_position,
            velocity=self.velocity_position,
        )

        (
            focal_point,
            self.velocity_focal,
        ) = self.inertial_filter(
            current=self.previous_focal,
            target=focal_point,
            velocity=self.velocity_focal,
        )

        self.previous_position = (
            camera_position.copy()
        )

        self.previous_focal = (
            focal_point.copy()
        )

        return (
            camera_position,
            focal_point,
            index,
        )