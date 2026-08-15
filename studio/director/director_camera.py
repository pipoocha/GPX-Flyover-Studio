import numpy as np

import config
from studio.director.orientation import OrientationController


class DirectorCamera:
    """Caméra cinématique adaptative fondée sur les distances réelles.

    Le moteur reste compatible avec ``DirectorEngine`` et renvoie toujours
    ``(position, focal_point, index)``. Les réglages historiques restent
    utilisables, mais les valeurs sont désormais adaptées automatiquement à
    la longueur, au relief, à la pente et à la courbure locales du parcours.
    """

    def __init__(self, path_coords):
        self.coords = np.asarray(path_coords, dtype=float)
        if self.coords.ndim != 2 or self.coords.shape[1] < 3:
            raise ValueError("La trajectoire doit contenir des points X, Y, Z.")
        if len(self.coords) < 2:
            raise ValueError("La trajectoire doit contenir au moins deux points.")
        if not np.all(np.isfinite(self.coords[:, :3])):
            raise ValueError("La trajectoire contient des coordonnées invalides.")

        self.coords = self.coords[:, :3].copy()
        self._remove_duplicate_points()
        if len(self.coords) < 2:
            raise ValueError("La trajectoire ne contient pas assez de points distincts.")

        self.xy = self.coords[:, :2]
        self.center = self.coords.mean(axis=0)
        self.min_xy = self.xy.min(axis=0)
        self.max_xy = self.xy.max(axis=0)
        extent = self.max_xy - self.min_xy
        self.size = float(max(extent[0], extent[1], 1.0))
        self.min_z = float(self.coords[:, 2].min())
        self.max_z = float(self.coords[:, 2].max())
        self.relief_range = max(1.0, self.max_z - self.min_z)

        segment_xy = np.diff(self.xy, axis=0)
        self.segment_lengths = np.linalg.norm(segment_xy, axis=1)
        self.cumulative_distance = np.concatenate(
            ([0.0], np.cumsum(self.segment_lengths))
        )
        self.total_distance = float(self.cumulative_distance[-1])
        if self.total_distance < 1.0:
            raise ValueError("La trajectoire est trop courte pour calculer la caméra.")

        self.typical_spacing = self._percentile_positive(self.segment_lengths, 50, 1.0)
        self.route_scale = self._route_scale()

        orientation_mode = getattr(config, "CAMERA_ORIENTATION_MODE", "route")
        orientation_angle = getattr(config, "CAMERA_ORIENTATION_ANGLE", 0.0)
        self.orientation = OrientationController(
            self.coords,
            mode=orientation_mode,
            angle=orientation_angle,
        )

        self.predictive_enabled = bool(
            getattr(config, "PREDICTIVE_CAMERA_ENABLED", True)
        )
        legacy_look_points = max(2.0, float(getattr(config, "LOOK_AHEAD", 420)))
        legacy_look_distance = legacy_look_points * self.typical_spacing
        automatic_look_distance = self.clamp(
            self.total_distance * 0.018,
            180.0,
            1800.0,
        )
        self.base_look_distance = float(
            getattr(
                config,
                "CAMERA_LOOK_AHEAD_DISTANCE",
                max(automatic_look_distance, min(legacy_look_distance, 1800.0)),
            )
        )
        self.min_look_distance = float(
            getattr(
                config,
                "CAMERA_MIN_LOOK_AHEAD_DISTANCE",
                max(80.0, self.base_look_distance * 0.38),
            )
        )
        self.max_look_distance = float(
            getattr(
                config,
                "CAMERA_MAX_LOOK_AHEAD_DISTANCE",
                max(self.min_look_distance, self.base_look_distance * 1.85),
            )
        )
        self.analysis_distance = float(
            getattr(
                config,
                "CAMERA_ANALYSIS_DISTANCE",
                self.clamp(self.base_look_distance * 0.65, 120.0, 1100.0),
            )
        )
        self.relief_window_distance = float(
            getattr(
                config,
                "CAMERA_RELIEF_WINDOW_DISTANCE",
                self.clamp(self.base_look_distance * 2.0, 500.0, 4200.0),
            )
        )

        self.curvature_strength = float(
            getattr(config, "PREDICTIVE_CURVATURE_STRENGTH", 0.85)
        )
        self.slope_strength = float(
            getattr(config, "PREDICTIVE_SLOPE_STRENGTH", 1.0)
        )
        self.relief_strength = float(
            getattr(config, "PREDICTIVE_RELIEF_STRENGTH", 0.75)
        )
        self.position_smoothing = self.clamp(
            float(getattr(config, "PREDICTIVE_POSITION_SMOOTHING", 0.10)),
            0.01,
            1.0,
        )
        self.focal_smoothing = self.clamp(
            float(getattr(config, "PREDICTIVE_FOCAL_SMOOTHING", 0.13)),
            0.01,
            1.0,
        )
        self.parameter_smoothing = self.clamp(
            float(getattr(config, "CAMERA_PARAMETER_SMOOTHING", 0.10)),
            0.01,
            1.0,
        )

        self.local_fit_enabled = bool(
            getattr(config, "CAMERA_LOCAL_FIT_ENABLED", True)
        )
        self.min_distance = float(
            getattr(config, "CAMERA_LOCAL_FIT_MIN_DISTANCE", 700.0)
        )
        self.max_distance = float(
            getattr(config, "CAMERA_LOCAL_FIT_MAX_DISTANCE", 4800.0)
        )
        self.min_height = float(
            getattr(config, "CAMERA_LOCAL_FIT_MIN_HEIGHT", 350.0)
        )
        self.max_height = float(
            getattr(config, "CAMERA_LOCAL_FIT_MAX_HEIGHT", 2800.0)
        )

        self.lateral_enabled = bool(getattr(config, "CAMERA_LATERAL_ENABLED", True))
        self.lateral_minimum = float(
            getattr(config, "CAMERA_LATERAL_MINIMUM", 120.0)
        )
        self.lateral_maximum = float(
            getattr(config, "CAMERA_LATERAL_MAXIMUM", 1050.0)
        )
        self.orientation_blend = self.clamp(
            float(getattr(config, "CAMERA_LATERAL_DIRECTION_BLEND", 0.45)),
            0.0,
            1.0,
        )

        self.endpoint_window = self.clamp(
            float(getattr(config, "CAMERA_ENDPOINT_WINDOW", 0.075)),
            0.0,
            0.25,
        )
        self.focal_height = float(getattr(config, "FOCAL_HEIGHT", 220.0))

        # Lecture de la pente longitudinale à plusieurs horizons. Elle évite
        # l'illusion visuelle d'une vallée descendante qui semblerait monter.
        self.grade_reading_enabled = bool(
            getattr(config, "CAMERA_GRADE_READING_ENABLED", True)
        )
        self.grade_horizons = tuple(
            float(v) for v in getattr(
                config, "CAMERA_GRADE_HORIZONS", (300.0, 800.0, 1500.0)
            )
        )
        self.grade_weights = np.asarray(
            getattr(config, "CAMERA_GRADE_WEIGHTS", (0.50, 0.32, 0.18)),
            dtype=float,
        )
        if len(self.grade_weights) != len(self.grade_horizons):
            self.grade_weights = np.ones(len(self.grade_horizons), dtype=float)
        self.grade_weights /= max(float(self.grade_weights.sum()), 1e-9)
        self.descent_focal_strength = float(
            getattr(config, "CAMERA_DESCENT_FOCAL_STRENGTH", 1.0)
        )
        self.ascent_focal_strength = float(
            getattr(config, "CAMERA_ASCENT_FOCAL_STRENGTH", 0.55)
        )

        self.previous_position = None
        self.previous_focal = None
        self.previous_direction = None
        self.previous_side_sign = 1.0
        self.previous_look_distance = self.base_look_distance
        self.previous_camera_distance = self._base_camera_distance()
        self.previous_camera_height = self._base_camera_height()
        self.previous_lateral_offset = self.clamp(
            float(getattr(config, "SIDE_OFFSET", 450.0)),
            self.lateral_minimum,
            self.lateral_maximum,
        )

    def _remove_duplicate_points(self):
        delta = np.diff(self.coords[:, :2], axis=0)
        keep = np.concatenate(([True], np.linalg.norm(delta, axis=1) > 1e-6))
        self.coords = self.coords[keep]

    @staticmethod
    def _percentile_positive(values, percentile, default):
        values = np.asarray(values, dtype=float)
        values = values[values > 1e-9]
        if len(values) == 0:
            return float(default)
        return float(np.percentile(values, percentile))

    def _route_scale(self):
        horizontal = max(self.size, 1.0)
        vertical = max(self.relief_range * 1.8, 1.0)
        return float(max(horizontal, vertical))

    @staticmethod
    def clamp(value, minimum, maximum):
        return max(minimum, min(maximum, float(value)))

    @staticmethod
    def smoothstep(value):
        value = DirectorCamera.clamp(value, 0.0, 1.0)
        return value * value * (3.0 - 2.0 * value)

    @staticmethod
    def normalize(vector, fallback=None):
        vector = np.asarray(vector, dtype=float)
        norm = float(np.linalg.norm(vector))
        if norm < 1e-9:
            if fallback is None:
                fallback = np.array([0.0, 1.0, 0.0], dtype=float)
            return np.asarray(fallback, dtype=float).copy()
        return vector / norm

    @staticmethod
    def _blend(previous, target, alpha):
        target = np.asarray(target, dtype=float)
        if previous is None:
            return target.copy()
        return np.asarray(previous, dtype=float) * (1.0 - alpha) + target * alpha

    def _smooth_scalar(self, previous, target):
        return previous * (1.0 - self.parameter_smoothing) + target * self.parameter_smoothing

    def distance_at_progress(self, progress):
        return self.clamp(progress, 0.0, 1.0) * self.total_distance

    def index_at_distance(self, distance):
        distance = self.clamp(distance, 0.0, self.total_distance)
        return int(
            np.clip(
                np.searchsorted(self.cumulative_distance, distance, side="right") - 1,
                0,
                len(self.coords) - 1,
            )
        )

    def point_at_distance(self, distance):
        distance = self.clamp(distance, 0.0, self.total_distance)
        index = self.index_at_distance(distance)
        if index >= len(self.coords) - 1:
            return self.coords[-1].copy(), len(self.coords) - 1
        start_distance = self.cumulative_distance[index]
        segment_length = max(self.segment_lengths[index], 1e-9)
        factor = self.clamp((distance - start_distance) / segment_length, 0.0, 1.0)
        point = self.coords[index] * (1.0 - factor) + self.coords[index + 1] * factor
        return point, index

    def point_at(self, progress):
        return self.point_at_distance(self.distance_at_progress(progress))

    def direction_at_distance(self, distance, window=None):
        """Direction horizontale de la trace, utilisée pour courbure et latéralité."""
        window = self.analysis_distance * 0.35 if window is None else float(window)
        before, _ = self.point_at_distance(distance - window)
        after, _ = self.point_at_distance(distance + window)
        direction = after - before
        direction[2] = 0.0
        return self.normalize(direction, self.previous_direction)

    def direction_3d_at_distance(self, distance, window=None):
        """Direction réelle de la vallée, pente verticale comprise.

        Contrairement à ``direction_at_distance``, cette direction n'est pas
        aplatie. Elle sert au placement longitudinal de la caméra afin qu'une
        vallée descendante soit visuellement lue comme descendante.
        """
        window = self.analysis_distance * 0.55 if window is None else float(window)
        before, _ = self.point_at_distance(distance - window)
        after, _ = self.point_at_distance(distance + window)
        direction = after - before
        fallback = self.previous_direction
        if fallback is None:
            fallback = np.array([1.0, 0.0, 0.0], dtype=float)
        return self.normalize(direction, fallback)

    def curvature_at_distance(self, distance):
        window = self.analysis_distance
        before = self.direction_at_distance(distance - window * 0.55, window * 0.45)
        after = self.direction_at_distance(distance + window * 0.55, window * 0.45)
        dot_value = self.clamp(np.dot(before, after), -1.0, 1.0)
        angle = float(np.arccos(dot_value))
        return self.clamp(angle / (np.pi * 0.65), 0.0, 1.0)

    def signed_turn_at_distance(self, distance):
        window = self.analysis_distance
        before = self.direction_at_distance(distance - window * 0.45, window * 0.35)
        after = self.direction_at_distance(distance + window * 0.45, window * 0.35)
        return float(before[0] * after[1] - before[1] * after[0])

    def slope_at_distance(self, distance):
        window = self.analysis_distance * 0.55
        before, _ = self.point_at_distance(distance - window)
        after, _ = self.point_at_distance(distance + window)
        horizontal = float(np.linalg.norm(after[:2] - before[:2]))
        if horizontal < 1e-6:
            return 0.0
        return self.clamp((after[2] - before[2]) / horizontal, -0.75, 0.75)

    def longitudinal_grade(self, distance):
        """Pente aval pondérée à 300/800/1500 m environ.

        Une valeur négative signifie que l'itinéraire descend devant la
        caméra. L'utilisation de plusieurs horizons rend le cadrage stable
        même quand le GPX comporte de petites bosses locales.
        """
        if not self.grade_reading_enabled:
            return self.slope_at_distance(distance), 0.0

        origin, _ = self.point_at_distance(distance)
        grades = []
        drops = []
        weights = []
        remaining = max(0.0, self.total_distance - distance)
        for horizon, weight in zip(self.grade_horizons, self.grade_weights):
            actual = min(float(horizon), remaining)
            if actual < 40.0:
                continue
            ahead, _ = self.point_at_distance(distance + actual)
            horizontal = float(np.linalg.norm(ahead[:2] - origin[:2]))
            if horizontal < 1.0:
                continue
            grades.append((ahead[2] - origin[2]) / horizontal)
            drops.append(ahead[2] - origin[2])
            weights.append(float(weight))

        if not grades:
            return self.slope_at_distance(distance), 0.0
        weights = np.asarray(weights, dtype=float)
        weights /= max(float(weights.sum()), 1e-9)
        grade = float(np.dot(np.asarray(grades), weights))
        drop = float(np.dot(np.asarray(drops), weights))
        return self.clamp(grade, -0.55, 0.55), drop

    def local_relief(self, distance):
        start = self.index_at_distance(distance - self.relief_window_distance * 0.30)
        end = self.index_at_distance(distance + self.relief_window_distance)
        end = min(len(self.coords) - 1, max(start + 1, end))
        points = self.coords[start : end + 1]
        local_range = float(np.ptp(points[:, 2])) if len(points) else 0.0
        scale = max(180.0, min(self.relief_range, self.relief_window_distance * 0.55))
        return self.clamp(local_range / scale, 0.0, 1.0), local_range

    def local_max_altitude(self, distance):
        start = self.index_at_distance(distance - self.analysis_distance)
        end = self.index_at_distance(distance + self.relief_window_distance)
        end = min(len(self.coords) - 1, max(start, end))
        return float(np.max(self.coords[start : end + 1, 2]))

    def _base_camera_distance(self):
        automatic = self.route_scale * 0.27 + np.sqrt(self.total_distance) * 6.0
        if not self.local_fit_enabled:
            automatic = max(automatic, float(getattr(config, "CAMERA_DISTANCE", 2800.0)))
        return self.clamp(automatic, self.min_distance, self.max_distance)

    def _base_camera_height(self):
        automatic = self.route_scale * 0.13 + self.relief_range * 0.24
        if not self.local_fit_enabled:
            automatic = max(automatic, float(getattr(config, "CAMERA_HEIGHT", 1400.0)))
        return self.clamp(automatic, self.min_height, self.max_height)

    def predictive_look_distance(self, distance, curvature, slope, relief):
        if not self.predictive_enabled:
            return self.base_look_distance
        straight_factor = 1.0 + (1.0 - curvature) * 0.28
        curve_factor = 1.0 - curvature * self.curvature_strength * 0.52
        slope_factor = 1.0 - min(abs(slope), 0.35) * self.slope_strength * 0.65
        relief_factor = 1.0 + relief * self.relief_strength * 0.20
        target = self.base_look_distance * straight_factor * curve_factor * slope_factor * relief_factor
        remaining = max(0.0, self.total_distance - distance)
        target = min(target, max(self.min_look_distance, remaining))
        target = self.clamp(target, self.min_look_distance, self.max_look_distance)
        self.previous_look_distance = self._smooth_scalar(self.previous_look_distance, target)
        return self.previous_look_distance

    def adaptive_framing(self, curvature, slope, relief, local_relief):
        distance = self._base_camera_distance()
        distance *= 1.0 + relief * 0.38 + min(local_relief / 2000.0, 1.0) * 0.20
        distance *= 1.0 - curvature * 0.20
        distance *= 1.0 + min(abs(slope), 0.35) * 0.18
        distance = self.clamp(distance, self.min_distance, self.max_distance)

        height = self._base_camera_height()
        height += local_relief * 0.28
        height *= 1.0 + relief * 0.30 + max(0.0, slope) * 0.45
        height = self.clamp(height, self.min_height, self.max_height)

        self.previous_camera_distance = self._smooth_scalar(
            self.previous_camera_distance, distance
        )
        self.previous_camera_height = self._smooth_scalar(
            self.previous_camera_height, height
        )
        return self.previous_camera_distance, self.previous_camera_height

    def outside_turn_side(self, signed_turn):
        if abs(signed_turn) > 0.025:
            target = -1.0 if signed_turn > 0.0 else 1.0
        else:
            target = self.previous_side_sign
        self.previous_side_sign = self._smooth_scalar(self.previous_side_sign, target)
        if abs(self.previous_side_sign) < 0.12:
            self.previous_side_sign = 0.12 if target >= 0.0 else -0.12
        return self.previous_side_sign

    def adaptive_lateral_offset(self, camera_distance, curvature, relief):
        if not self.lateral_enabled:
            return 0.0
        target = camera_distance * (0.10 + curvature * 0.055 + relief * 0.045)
        target = self.clamp(target, self.lateral_minimum, self.lateral_maximum)
        self.previous_lateral_offset = self._smooth_scalar(
            self.previous_lateral_offset, target
        )
        return self.previous_lateral_offset

    def endpoint_wide_camera(self, progress, direction, side, position, focal):
        if self.endpoint_window <= 0.0:
            return position, focal
        if progress < self.endpoint_window:
            strength = 1.0 - progress / self.endpoint_window
            anchor = self.coords[0]
            route_target, _ = self.point_at_distance(
                min(self.total_distance, self.base_look_distance * 1.8)
            )
        elif progress > 1.0 - self.endpoint_window:
            strength = (progress - (1.0 - self.endpoint_window)) / self.endpoint_window
            anchor = self.coords[-1]
            route_target, _ = self.point_at_distance(
                max(0.0, self.total_distance - self.base_look_distance * 1.5)
            )
        else:
            return position, focal

        strength = self.smoothstep(strength)
        wide_distance = self.clamp(self._base_camera_distance() * 1.55, 1500.0, 6200.0)
        wide_height = self.clamp(self._base_camera_height() * 1.55, 750.0, 3400.0)
        wide_position = anchor - direction * wide_distance + side * wide_distance * 0.16
        wide_position[2] = max(anchor[2] + wide_height, self.local_max_altitude(self.distance_at_progress(progress)) + wide_height * 0.28)
        wide_focal = anchor * 0.66 + route_target * 0.34
        return (
            position * (1.0 - strength) + wide_position * strength,
            focal * (1.0 - strength) + wide_focal * strength,
        )

    def camera_at_progress(self, progress):
        progress = self.clamp(progress, 0.0, 1.0)
        distance = self.distance_at_progress(progress)
        active, index = self.point_at_distance(distance)

        curvature = self.curvature_at_distance(distance)
        slope = self.slope_at_distance(distance)
        grade, forward_drop = self.longitudinal_grade(distance)
        # Le profil multi-horizon est prioritaire pour la lecture visuelle ;
        # la pente locale reste présente pour réagir aux ruptures proches.
        visual_slope = slope * 0.35 + grade * 0.65
        relief, local_relief = self.local_relief(distance)
        look_distance = self.predictive_look_distance(
            distance, curvature, visual_slope, relief
        )

        middle_point, _ = self.point_at_distance(distance + look_distance * 0.48)
        look_point, _ = self.point_at_distance(distance + look_distance)
        horizontal_direction = self.direction_at_distance(
            distance, self.analysis_distance * 0.45
        )
        slope_direction = self.direction_3d_at_distance(
            distance, self.analysis_distance * 0.70
        )

        orientation_direction = self.orientation.direction_at_progress(progress)
        orientation_direction = np.asarray(orientation_direction, dtype=float)
        # L'orientation du réalisateur choisit l'azimut, mais la composante Z
        # doit rester celle de la pente réelle de la vallée.
        orientation_direction[2] = slope_direction[2]
        orientation_direction = self.normalize(orientation_direction, slope_direction)
        direction = self.normalize(
            orientation_direction * (1.0 - self.orientation_blend)
            + slope_direction * self.orientation_blend,
            slope_direction,
        )
        self.previous_direction = direction.copy()

        # Le décalage latéral reste strictement horizontal pour ne pas incliner
        # artificiellement la caméra sur les flancs de vallée.
        side = np.array([-horizontal_direction[1], horizontal_direction[0], 0.0], dtype=float)
        side = self.normalize(side, np.array([0.0, 1.0, 0.0], dtype=float))
        camera_distance, camera_height = self.adaptive_framing(
            curvature, visual_slope, relief, local_relief
        )

        moving_center = active * 0.60 + middle_point * 0.27 + look_point * 0.13
        # Placement derrière le parcours dans son axe 3D réel. Sur une
        # descente, la caméra se retrouve naturellement plus haute que le point
        # visé ; sur une montée, l'inverse se produit.
        camera_position = moving_center - direction * camera_distance
        camera_position[2] += camera_height
        signed_turn = self.signed_turn_at_distance(distance)
        side_sign = self.outside_turn_side(signed_turn)
        lateral_offset = self.adaptive_lateral_offset(
            camera_distance, curvature, relief
        )
        camera_position += side * lateral_offset * side_sign

        local_high = self.local_max_altitude(distance)
        terrain_clearance = max(camera_height * 0.22, 180.0 + local_relief * 0.08)
        # Ne plus réinitialiser Z à ``moving_center + camera_height`` : cela
        # annulait la pente 3D calculée juste au-dessus. On impose seulement
        # une altitude minimale de sécurité au-dessus du terrain.
        camera_position[2] = max(
            camera_position[2],
            local_high + terrain_clearance,
        )

        focal_point = active * 0.20 + middle_point * 0.37 + look_point * 0.43

        # Le point visé doit suivre l'aval réel de la vallée. Sur une descente,
        # l'ancien FOCAL_HEIGHT relevait artificiellement l'horizon et pouvait
        # faire paraître la vallée montante. On réduit donc cette hauteur et
        # on incline explicitement le regard vers l'aval.
        base_focal_height = self.focal_height + relief * camera_height * 0.05
        if visual_slope < -0.008:
            descent = self.clamp(-visual_slope / 0.18, 0.0, 1.0)
            base_focal_height *= 1.0 - 0.78 * descent
            downhill_bias = min(abs(forward_drop) * 0.34, camera_height * 0.34)
            focal_point[2] -= downhill_bias * self.descent_focal_strength
        elif visual_slope > 0.008:
            ascent = self.clamp(visual_slope / 0.18, 0.0, 1.0)
            focal_point[2] += (
                ascent * camera_height * 0.10 * self.ascent_focal_strength
            )

        focal_point[2] += base_focal_height

        camera_position, focal_point = self.endpoint_wide_camera(
            progress,
            direction,
            side,
            camera_position,
            focal_point,
        )

        camera_position = self._blend(
            self.previous_position,
            camera_position,
            self.position_smoothing,
        )
        focal_point = self._blend(
            self.previous_focal,
            focal_point,
            self.focal_smoothing,
        )
        self.previous_position = camera_position.copy()
        self.previous_focal = focal_point.copy()
        return camera_position, focal_point, index
