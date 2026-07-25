from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import math
import xml.etree.ElementTree as ET


EARTH_RADIUS_M = 6_371_000.0


@dataclass
class GPXAnalysis:
    name: str
    point_count: int

    distance_km: float
    ascent_m: float
    descent_m: float

    min_elevation_m: float
    max_elevation_m: float
    mean_elevation_m: float
    elevation_range_m: float

    mean_grade_percent: float
    max_grade_percent: float

    bbox_width_km: float
    bbox_height_km: float
    bbox_area_km2: float

    relief_index: int
    difficulty_index: int
    difficulty_label: str
    terrain_profile: str

    suggested_style: str
    suggested_quality: str
    suggested_duration_seconds: int

    def to_dict(self) -> dict:
        return asdict(self)


class GPXAnalyzer:
    def __init__(
        self,
        gpx_file: str | Path,
        *,
        elevation_noise_threshold_m: float = 2.0,
        max_reasonable_grade_percent: float = 80.0,
    ):
        self.gpx_file = Path(gpx_file)
        self.elevation_noise_threshold_m = float(
            elevation_noise_threshold_m
        )
        self.max_reasonable_grade_percent = float(
            max_reasonable_grade_percent
        )

    @staticmethod
    def haversine_m(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)

        delta_lat = lat2_r - lat1_r
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2.0) ** 2
            + math.cos(lat1_r)
            * math.cos(lat2_r)
            * math.sin(delta_lon / 2.0) ** 2
        )

        return (
            2.0
            * EARTH_RADIUS_M
            * math.atan2(
                math.sqrt(a),
                math.sqrt(max(0.0, 1.0 - a)),
            )
        )

    def _read_points(self) -> list[tuple[float, float, float]]:
        if not self.gpx_file.exists():
            raise FileNotFoundError(
                f"GPX introuvable : {self.gpx_file}"
            )

        if self.gpx_file.suffix.lower() != ".gpx":
            raise ValueError(
                f"Le fichier doit être au format GPX : {self.gpx_file}"
            )

        root = ET.parse(self.gpx_file).getroot()
        points: list[tuple[float, float, float]] = []

        last_elevation = 0.0

        for element in root.iter():
            if not element.tag.endswith("trkpt"):
                continue

            latitude = float(element.attrib["lat"])
            longitude = float(element.attrib["lon"])

            elevation = None

            for child in element:
                if child.tag.endswith("ele") and child.text:
                    elevation = float(child.text)
                    break

            if elevation is None:
                elevation = last_elevation

            last_elevation = float(elevation)

            points.append(
                (
                    latitude,
                    longitude,
                    float(elevation),
                )
            )

        if len(points) < 2:
            raise ValueError(
                "Le GPX ne contient pas assez de points."
            )

        return points

    def _calculate_geometry(
        self,
        points: list[tuple[float, float, float]],
    ):
        total_distance_m = 0.0
        ascent_m = 0.0
        descent_m = 0.0

        grades: list[float] = []

        latitudes = [point[0] for point in points]
        longitudes = [point[1] for point in points]
        elevations = [point[2] for point in points]

        for previous, current in zip(
            points[:-1],
            points[1:],
        ):
            horizontal_m = self.haversine_m(
                previous[0],
                previous[1],
                current[0],
                current[1],
            )

            elevation_delta = current[2] - previous[2]

            total_distance_m += horizontal_m

            if elevation_delta >= self.elevation_noise_threshold_m:
                ascent_m += elevation_delta
            elif elevation_delta <= -self.elevation_noise_threshold_m:
                descent_m += -elevation_delta

            if horizontal_m >= 3.0:
                grade = (
                    elevation_delta
                    / horizontal_m
                    * 100.0
                )

                if abs(grade) <= self.max_reasonable_grade_percent:
                    grades.append(abs(grade))

        min_lat = min(latitudes)
        max_lat = max(latitudes)
        min_lon = min(longitudes)
        max_lon = max(longitudes)

        mid_lat = (min_lat + max_lat) / 2.0
        mid_lon = (min_lon + max_lon) / 2.0

        bbox_height_m = self.haversine_m(
            min_lat,
            mid_lon,
            max_lat,
            mid_lon,
        )

        bbox_width_m = self.haversine_m(
            mid_lat,
            min_lon,
            mid_lat,
            max_lon,
        )

        mean_grade = (
            sum(grades) / len(grades)
            if grades
            else 0.0
        )

        max_grade = (
            max(grades)
            if grades
            else 0.0
        )

        return {
            "distance_km": total_distance_m / 1000.0,
            "ascent_m": ascent_m,
            "descent_m": descent_m,
            "min_elevation_m": min(elevations),
            "max_elevation_m": max(elevations),
            "mean_elevation_m": sum(elevations) / len(elevations),
            "elevation_range_m": max(elevations) - min(elevations),
            "mean_grade_percent": mean_grade,
            "max_grade_percent": max_grade,
            "bbox_width_km": bbox_width_m / 1000.0,
            "bbox_height_km": bbox_height_m / 1000.0,
            "bbox_area_km2": (
                bbox_width_m
                * bbox_height_m
                / 1_000_000.0
            ),
        }

    @staticmethod
    def _clamp_index(value: float) -> int:
        return max(
            0,
            min(
                100,
                int(round(value)),
            ),
        )

    def _relief_index(self, geometry: dict) -> int:
        distance_km = max(
            1.0,
            geometry["distance_km"],
        )

        ascent_per_km = (
            geometry["ascent_m"]
            / distance_km
        )

        score = (
            geometry["elevation_range_m"] / 28.0
            + ascent_per_km * 0.55
            + geometry["mean_grade_percent"] * 2.0
            + geometry["max_elevation_m"] / 450.0
        )

        return self._clamp_index(score)

    def _difficulty_index(self, geometry: dict) -> int:
        score = (
            geometry["distance_km"] * 0.55
            + geometry["ascent_m"] / 85.0
            + geometry["max_elevation_m"] / 230.0
            + geometry["mean_grade_percent"] * 1.5
        )

        return self._clamp_index(score)

    @staticmethod
    def _difficulty_label(index: int) -> str:
        if index < 20:
            return "Facile"
        if index < 40:
            return "Modéré"
        if index < 60:
            return "Difficile"
        if index < 80:
            return "Très difficile"
        return "Extrême"

    @staticmethod
    def _terrain_profile(
        geometry: dict,
        relief_index: int,
    ) -> str:
        max_elevation = geometry["max_elevation_m"]
        elevation_range = geometry["elevation_range_m"]
        ascent_per_km = (
            geometry["ascent_m"]
            / max(
                1.0,
                geometry["distance_km"],
            )
        )

        if (
            max_elevation >= 4200
            or elevation_range >= 2200
        ):
            return "Himalaya"

        if (
            max_elevation >= 2500
            or elevation_range >= 1300
            or relief_index >= 72
        ):
            return "Haute montagne"

        if (
            max_elevation >= 1200
            or elevation_range >= 650
            or ascent_per_km >= 45
            or relief_index >= 48
        ):
            return "Moyenne montagne"

        if (
            elevation_range >= 220
            or ascent_per_km >= 20
            or relief_index >= 25
        ):
            return "Collines"

        return "Plaine"

    @staticmethod
    def _suggest_style(
        terrain_profile: str,
        distance_km: float,
    ) -> str:
        if terrain_profile == "Plaine":
            return (
                "Tour de France"
                if distance_km >= 25
                else "Drone"
            )

        if terrain_profile == "Collines":
            return "Tour de France"

        if terrain_profile == "Moyenne montagne":
            return "Hélicoptère"

        if terrain_profile in {
            "Haute montagne",
            "Himalaya",
        }:
            return "Cinéma"

        return "Director"

    @staticmethod
    def _suggest_quality(
        point_count: int,
        distance_km: float,
    ) -> str:
        if (
            point_count > 12000
            or distance_km > 180
        ):
            return "Standard"

        if (
            point_count > 5000
            or distance_km > 90
        ):
            return "Haute"

        return "Haute"

    @staticmethod
    def _suggest_duration(
        distance_km: float,
        terrain_profile: str,
    ) -> int:
        if distance_km < 8:
            duration = 30
        elif distance_km < 20:
            duration = 45
        elif distance_km < 45:
            duration = 60
        elif distance_km < 90:
            duration = 90
        elif distance_km < 160:
            duration = 120
        else:
            duration = 180

        if terrain_profile in {
            "Haute montagne",
            "Himalaya",
        }:
            duration = int(
                round(
                    duration * 1.20
                )
            )

        return duration

    def analyze(self) -> GPXAnalysis:
        points = self._read_points()
        geometry = self._calculate_geometry(points)

        relief_index = self._relief_index(
            geometry
        )

        difficulty_index = self._difficulty_index(
            geometry
        )

        terrain_profile = self._terrain_profile(
            geometry,
            relief_index,
        )

        suggested_style = self._suggest_style(
            terrain_profile,
            geometry["distance_km"],
        )

        suggested_quality = self._suggest_quality(
            len(points),
            geometry["distance_km"],
        )

        suggested_duration = self._suggest_duration(
            geometry["distance_km"],
            terrain_profile,
        )

        return GPXAnalysis(
            name=self.gpx_file.stem,
            point_count=len(points),

            distance_km=round(
                geometry["distance_km"],
                2,
            ),
            ascent_m=round(
                geometry["ascent_m"],
                0,
            ),
            descent_m=round(
                geometry["descent_m"],
                0,
            ),

            min_elevation_m=round(
                geometry["min_elevation_m"],
                0,
            ),
            max_elevation_m=round(
                geometry["max_elevation_m"],
                0,
            ),
            mean_elevation_m=round(
                geometry["mean_elevation_m"],
                0,
            ),
            elevation_range_m=round(
                geometry["elevation_range_m"],
                0,
            ),

            mean_grade_percent=round(
                geometry["mean_grade_percent"],
                1,
            ),
            max_grade_percent=round(
                geometry["max_grade_percent"],
                1,
            ),

            bbox_width_km=round(
                geometry["bbox_width_km"],
                2,
            ),
            bbox_height_km=round(
                geometry["bbox_height_km"],
                2,
            ),
            bbox_area_km2=round(
                geometry["bbox_area_km2"],
                2,
            ),

            relief_index=relief_index,
            difficulty_index=difficulty_index,
            difficulty_label=self._difficulty_label(
                difficulty_index
            ),
            terrain_profile=terrain_profile,

            suggested_style=suggested_style,
            suggested_quality=suggested_quality,
            suggested_duration_seconds=suggested_duration,
        )


def analyze_gpx(
    gpx_file: str | Path,
) -> GPXAnalysis:
    return GPXAnalyzer(
        gpx_file
    ).analyze()
