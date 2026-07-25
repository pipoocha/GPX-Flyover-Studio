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

        # Cadrage latéral adaptatif :
        # la caméra se place à l'extérieur des virages et s'écarte
        # davantage lorsque le relief est marqué.
        self.lateral_enabled = bool(
            getattr(
                config,
                "CAMERA_LATERAL_ENABLED",
                True,
            )
        )

        self.lateral_direction_blend = float(
            getattr(
                config,
                "CAMERA_LATERAL_DIRECTION_BLEND",
                0.55,
            )
        )

        self.lateral_distance_scale = float(
            getattr(
                config,
                "CAMERA_LATERAL_DISTANCE_SCALE",
                0.15,
            )
        )

        self.lateral_minimum = float(
            getattr(
                config,
                "CAMERA_LATERAL_MINIMUM",
                180.0,
            )
        )

        self.lateral_maximum = float(
            getattr(
                config,
                "CAMERA_LATERAL_MAXIMUM",
                850.0,
            )
        )

        self.lateral_smoothing = float(
            getattr(
                config,
                "CAMERA_LATERAL_SMOOTHING",
                0.06,
            )
        )

        self.previous_side_sign = 1.0
        self.previous_lateral_offset = float(
            getattr(
                config,
                "SIDE_OFFSET",
                450.0,
            )
        )

        self.local_fit_enabled = bool(
            getattr(config, "CAMERA_LOCAL_FIT_ENABLED", True)
        )
        self.local_fit_distance_scale = float(
            getattr(config, "CAMERA_LOCAL_FIT_DISTANCE_SCALE", 0.28)
        )
        self.local_fit_height_scale = float(
            getattr(config, "CAMERA_LOCAL_FIT_HEIGHT_SCALE", 0.13)
        )
        self.local_fit_min_distance = float(
            getattr(config, "CAMERA_LOCAL_FIT_MIN_DISTANCE", 900.0)
        )
        self.local_fit_max_distance = float(
            getattr(config, "CAMERA_LOCAL_FIT_MAX_DISTANCE", 2600.0)
        )
        self.local_fit_min_height = float(
            getattr(config, "CAMERA_LOCAL_FIT_MIN_HEIGHT", 420.0)
        )
        self.local_fit_max_height = float(
            getattr(config, "CAMERA_LOCAL_FIT_MAX_HEIGHT", 1350.0)
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
        if self.local_fit_enabled:
            base_height = self.clamp(
                self.size * self.local_fit_height_scale,
                self.local_fit_min_height,
                self.local_fit_max_height,
            )
        else:
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
        if self.local_fit_enabled:
            base_distance = self.clamp(
                self.size * self.local_fit_distance_scale,
                self.local_fit_min_distance,
                self.local_fit_max_distance,
            )
        else:
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

    def local_route_direction(
        self,
        index,
    ):
        window = self.analysis_window

        index_0 = max(
            0,
            index - window,
        )

        index_1 = min(
            len(self.coords) - 1,
            index + window,
        )

        return self.direction_between(
            index_0,
            index_1,
        )

    def outside_turn_side(
        self,
        index,
    ):
        """
        Renvoie le côté extérieur du virage.

        +1 et -1 représentent les deux côtés possibles de la trace.
        Sur une portion presque droite, on conserve le côté précédent
        afin d'éviter les changements incessants.
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

        direction_before = self.direction_between(
            index_0,
            index,
        )

        direction_after = self.direction_between(
            index,
            index_1,
        )

        cross_z = (
            direction_before[0]
            * direction_after[1]
            - direction_before[1]
            * direction_after[0]
        )

        if abs(cross_z) < 0.035:
            target_sign = self.previous_side_sign
        else:
            # Extérieur du virage : côté opposé au sens du virage.
            target_sign = -1.0 if cross_z > 0.0 else 1.0

        alpha = self.clamp(
            self.lateral_smoothing,
            0.001,
            1.0,
        )

        smoothed_sign = (
            self.previous_side_sign
            * (1.0 - alpha)
            + target_sign
            * alpha
        )

        if abs(smoothed_sign) < 0.08:
            smoothed_sign = (
                0.08
                if target_sign >= 0.0
                else -0.08
            )

        self.previous_side_sign = smoothed_sign

        return smoothed_sign

    def adaptive_lateral_offset(
        self,
        index,
        camera_distance,
    ):
        if not self.lateral_enabled:
            return float(
                getattr(
                    config,
                    "SIDE_OFFSET",
                    450.0,
                )
            )

        relief = self.relief_ahead(
            index
        )

        curvature = self.curvature_at(
            index
        )

        base_offset = (
            camera_distance
            * self.lateral_distance_scale
        )

        # Plus de décalage dans les zones encaissées et les virages.
        target_offset = base_offset * (
            1.0
            + relief * 0.55
            + curvature * 0.25
        )

        target_offset = self.clamp(
            target_offset,
            self.lateral_minimum,
            self.lateral_maximum,
        )

        alpha = self.clamp(
            self.lateral_smoothing,
            0.001,
            1.0,
        )

        smoothed_offset = (
            self.previous_lateral_offset
            * (1.0 - alpha)
            + target_offset
            * alpha
        )

        self.previous_lateral_offset = (
            smoothed_offset
        )

        return smoothed_offset

    def local_max_altitude(
        self,
        index,
        radius=None,
    ):
        if radius is None:
            radius = max(
                self.analysis_window,
                self.base_look_ahead // 2,
            )

        start = max(
            0,
            index - radius,
        )

        end = min(
            len(self.coords),
            index + radius + 1,
        )

        return float(
            self.coords[start:end, 2].max()
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

        orientation_direction = (
            self.orientation
            .direction_at_progress(
                progress
            )
        )

        orientation_direction = self.normalize(
            orientation_direction
        )

        local_direction = self.local_route_direction(
            index
        )

        blend = self.clamp(
            self.lateral_direction_blend,
            0.0,
            1.0,
        )

        direction = self.normalize(
            orientation_direction
            * (1.0 - blend)
            + local_direction
            * blend
        )

        side = np.array(
            [
                -direction[1],
                direction[0],
                0.0,
            ],
            dtype=float,
        )

        if self.local_fit_enabled:
            moving_center = (
                active * 0.62
                + middle_point * 0.25
                + look_point * 0.13
            )
        else:
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

        side_sign = self.outside_turn_side(
            index
        )

        lateral_offset = self.adaptive_lateral_offset(
            index=index,
            camera_distance=camera_distance,
        )

        camera_position += (
            side
            * lateral_offset
            * side_sign
        )

        local_max_z = self.local_max_altitude(
            index
        )

        clearance = max(
            180.0,
            camera_height * 0.22,
        )

        camera_position[2] = max(
            active[2] + camera_height,
            local_max_z + clearance,
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

        camera_position = (
            self.smooth_vector(
                self.previous_position,
                camera_position,
                self.position_smoothing,
            )
        )

        focal_point = self.smooth_vector(
            self.previous_focal,
            focal_point,
            self.focal_smoothing,
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