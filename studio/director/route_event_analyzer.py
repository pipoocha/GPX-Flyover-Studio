from dataclasses import dataclass

import numpy as np

from studio.animation.progress_path import ProgressPath


@dataclass
class RouteEvent:
    event_type: str
    progress: float
    distance: float
    altitude: float
    prominence: float = 0.0
    slope: float = 0.0
    index: int = 0

    @property
    def distance_km(self):
        return self.distance / 1000.0


class RouteEventAnalyzer:
    """
    Analyse le profil altimétrique de la trajectoire.

    Événements détectés :
    - high_point : point haut local ;
    - low_point : point bas local ;
    - steep_climb : forte montée ;
    - steep_descent : forte descente.

    Un point haut local n'est pas nécessairement un vrai sommet.
    """

    def __init__(
        self,
        path_coords,
        smoothing_window=41,
        prominence_threshold=20.0,
        minimum_spacing_m=300.0,
        steep_slope_threshold=0.08,
    ):
        self.coords = np.asarray(
            path_coords,
            dtype=float,
        )

        if len(self.coords) < 3:
            raise ValueError(
                "La trajectoire doit contenir au moins trois points."
            )

        self.progress_path = ProgressPath(
            self.coords
        )

        self.distances = np.asarray(
            self.progress_path.distances,
            dtype=float,
        )

        self.altitudes = self.coords[:, 2].astype(
            float
        )

        self.smoothing_window = max(
            3,
            int(smoothing_window),
        )

        if self.smoothing_window % 2 == 0:
            self.smoothing_window += 1

        self.prominence_threshold = float(
            prominence_threshold
        )

        self.minimum_spacing_m = float(
            minimum_spacing_m
        )

        self.steep_slope_threshold = float(
            steep_slope_threshold
        )

        self.smoothed_altitudes = (
            self.smooth_altitudes()
        )

        self.slopes = self.compute_slopes()

    def smooth_altitudes(self):
        window = min(
            self.smoothing_window,
            len(self.altitudes),
        )

        if window % 2 == 0:
            window -= 1

        if window < 3:
            return self.altitudes.copy()

        padding = window // 2

        padded = np.pad(
            self.altitudes,
            (padding, padding),
            mode="edge",
        )

        kernel = np.ones(
            window,
            dtype=float,
        ) / window

        return np.convolve(
            padded,
            kernel,
            mode="valid",
        )

    def compute_slopes(self):
        slopes = np.zeros(
            len(self.coords),
            dtype=float,
        )

        if len(self.coords) < 2:
            return slopes

        delta_distance = np.diff(
            self.distances
        )

        delta_altitude = np.diff(
            self.smoothed_altitudes
        )

        valid = delta_distance > 1e-6

        segment_slopes = np.zeros_like(
            delta_altitude
        )

        segment_slopes[valid] = (
            delta_altitude[valid]
            / delta_distance[valid]
        )

        slopes[1:] = segment_slopes

        return slopes

    def progress_at_index(self, index):
        if self.progress_path.total_distance <= 0:
            return 0.0

        return float(
            self.distances[index]
            / self.progress_path.total_distance
        )

    def prominence_at(self, index, radius=100):
        start = max(
            0,
            index - radius,
        )

        end = min(
            len(self.coords),
            index + radius + 1,
        )

        altitude = self.smoothed_altitudes[index]

        left_min = np.min(
            self.smoothed_altitudes[start:index + 1]
        )

        right_min = np.min(
            self.smoothed_altitudes[index:end]
        )

        reference = max(
            left_min,
            right_min,
        )

        return float(
            altitude - reference
        )

    def depth_at(self, index, radius=100):
        start = max(
            0,
            index - radius,
        )

        end = min(
            len(self.coords),
            index + radius + 1,
        )

        altitude = self.smoothed_altitudes[index]

        left_max = np.max(
            self.smoothed_altitudes[start:index + 1]
        )

        right_max = np.max(
            self.smoothed_altitudes[index:end]
        )

        reference = min(
            left_max,
            right_max,
        )

        return float(
            reference - altitude
        )

    def create_event(
        self,
        event_type,
        index,
        prominence=0.0,
        slope=0.0,
    ):
        return RouteEvent(
            event_type=event_type,
            progress=self.progress_at_index(index),
            distance=float(self.distances[index]),
            altitude=float(
                self.smoothed_altitudes[index]
            ),
            prominence=float(prominence),
            slope=float(slope),
            index=int(index),
        )

    def filter_by_spacing(self, events):
        if not events:
            return []

        events = sorted(
            events,
            key=lambda event: (
                event.distance,
                -event.prominence,
            ),
        )

        filtered = []

        for event in events:
            if not filtered:
                filtered.append(event)
                continue

            previous = filtered[-1]

            distance_difference = (
                event.distance
                - previous.distance
            )

            if (
                distance_difference
                >= self.minimum_spacing_m
            ):
                filtered.append(event)
                continue

            if event.prominence > previous.prominence:
                filtered[-1] = event

        return filtered

    def detect_high_points(self):
        events = []

        for index in range(
            1,
            len(self.coords) - 1,
        ):
            previous_altitude = (
                self.smoothed_altitudes[index - 1]
            )

            altitude = self.smoothed_altitudes[index]

            next_altitude = (
                self.smoothed_altitudes[index + 1]
            )

            if not (
                altitude > previous_altitude
                and altitude >= next_altitude
            ):
                continue

            prominence = self.prominence_at(
                index
            )

            if (
                prominence
                < self.prominence_threshold
            ):
                continue

            events.append(
                self.create_event(
                    event_type="high_point",
                    index=index,
                    prominence=prominence,
                    slope=self.slopes[index],
                )
            )

        return self.filter_by_spacing(events)

    def detect_low_points(self):
        events = []

        for index in range(
            1,
            len(self.coords) - 1,
        ):
            previous_altitude = (
                self.smoothed_altitudes[index - 1]
            )

            altitude = self.smoothed_altitudes[index]

            next_altitude = (
                self.smoothed_altitudes[index + 1]
            )

            if not (
                altitude < previous_altitude
                and altitude <= next_altitude
            ):
                continue

            depth = self.depth_at(index)

            if (
                depth
                < self.prominence_threshold
            ):
                continue

            events.append(
                self.create_event(
                    event_type="low_point",
                    index=index,
                    prominence=depth,
                    slope=self.slopes[index],
                )
            )

        return self.filter_by_spacing(events)

    def detect_steep_sections(self):
        events = []

        previous_type = None

        for index, slope in enumerate(
            self.slopes
        ):
            event_type = None

            if slope >= self.steep_slope_threshold:
                event_type = "steep_climb"

            elif slope <= -self.steep_slope_threshold:
                event_type = "steep_descent"

            if event_type is None:
                previous_type = None
                continue

            if event_type == previous_type:
                continue

            events.append(
                self.create_event(
                    event_type=event_type,
                    index=index,
                    slope=slope,
                )
            )

            previous_type = event_type

        return self.filter_by_spacing(events)

    def analyze(self):
        events = []

        events.extend(
            self.detect_high_points()
        )

        events.extend(
            self.detect_low_points()
        )

        events.extend(
            self.detect_steep_sections()
        )

        return sorted(
            events,
            key=lambda event: event.progress,
        )