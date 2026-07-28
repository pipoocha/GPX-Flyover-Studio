from __future__ import annotations

import math
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path


EARTH_RADIUS_M = 6_371_008.8


def _distance_m(a, b):
    lat1, lon1, _ = a
    lat2, lon2, _ = b
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(value)))


def _read_points(gpx_file):
    root = ET.parse(gpx_file).getroot()
    points = []

    for element in root.iter():
        if not (element.tag.endswith("trkpt") or element.tag.endswith("rtept")):
            continue

        elevation = None
        for child in element:
            if child.tag.endswith("ele") and child.text:
                try:
                    elevation = float(child.text)
                except ValueError:
                    pass
                break

        points.append(
            (
                float(element.attrib["lat"]),
                float(element.attrib["lon"]),
                elevation,
            )
        )

    if len(points) < 2:
        raise ValueError("Le GPX doit contenir au moins deux points.")

    return points


def _local_xy(points):
    mean_lat = statistics.fmean(point[0] for point in points)
    mean_lon = statistics.fmean(point[1] for point in points)
    cos_lat = math.cos(math.radians(mean_lat))

    return [
        (
            math.radians(lon - mean_lon) * EARTH_RADIUS_M * cos_lat,
            math.radians(lat - mean_lat) * EARTH_RADIUS_M,
        )
        for lat, lon, _ in points
    ]


def _convex_hull(points):
    points = sorted(set(points))
    if len(points) <= 1:
        return points

    def cross(o, a, b):
        return (
            (a[0] - o[0]) * (b[1] - o[1])
            - (a[1] - o[1]) * (b[0] - o[0])
        )

    lower = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def _polygon_area(points):
    if len(points) < 3:
        return 0.0

    return abs(
        sum(
            points[index][0] * points[(index + 1) % len(points)][1]
            - points[(index + 1) % len(points)][0] * points[index][1]
            for index in range(len(points))
        )
    ) / 2.0


def _median_smooth(values, window=5):
    radius = window // 2
    return [
        float(
            statistics.median(
                values[max(0, i - radius): min(len(values), i + radius + 1)]
            )
        )
        for i in range(len(values))
    ]


def _turn_angles_degrees(xy):
    angles = []

    for index in range(1, len(xy) - 1):
        ax = xy[index][0] - xy[index - 1][0]
        ay = xy[index][1] - xy[index - 1][1]
        bx = xy[index + 1][0] - xy[index][0]
        by = xy[index + 1][1] - xy[index][1]

        norm_a = math.hypot(ax, ay)
        norm_b = math.hypot(bx, by)

        if norm_a < 1e-9 or norm_b < 1e-9:
            continue

        cosine = max(
            -1.0,
            min(
                1.0,
                (ax * bx + ay * by) / (norm_a * norm_b),
            ),
        )

        angles.append(math.degrees(math.acos(cosine)))

    return angles


def _route_shape_scores(
    total_distance,
    start_end_distance,
    width,
    height,
    hull_area,
    bbox_area,
    segment_count,
    turn_angles,
):
    direct_ratio = start_end_distance / max(total_distance, 1.0)
    compactness = hull_area / max(bbox_area, 1.0)
    span = max(width, height, 1.0)
    elongation = max(width, height) / max(min(width, height), 1.0)

    repeated_density = total_distance / max(hull_area ** 0.5, 1.0)
    sharp_turn_ratio = (
        sum(angle >= 120.0 for angle in turn_angles)
        / max(1, len(turn_angles))
    )
    medium_turn_ratio = (
        sum(angle >= 60.0 for angle in turn_angles)
        / max(1, len(turn_angles))
    )

    loop_score = max(
        0.0,
        min(
            1.0,
            (1.0 - min(1.0, direct_ratio / 0.12))
            * 0.75
            + min(1.0, compactness / 0.65) * 0.25,
        ),
    )

    line_score = max(
        0.0,
        min(
            1.0,
            max(0.0, (direct_ratio - 0.55) / 0.40) * 0.80
            + min(1.0, elongation / 4.0) * 0.20,
        ),
    )

    out_and_back_score = max(
        0.0,
        min(
            1.0,
            (1.0 - min(1.0, direct_ratio / 0.20))
            * min(1.0, elongation / 3.0)
            * (0.65 + 0.35 * sharp_turn_ratio),
        ),
    )

    repeated_circuit_score = max(
        0.0,
        min(
            1.0,
            (1.0 - min(1.0, direct_ratio / 0.10))
            * min(1.0, repeated_density / 10.0)
            * (0.70 + 0.30 * medium_turn_ratio),
        ),
    )

    sinuous_score = max(
        0.0,
        min(
            1.0,
            medium_turn_ratio * 1.6,
        ),
    )

    raw = {
        "loop": loop_score,
        "line": line_score,
        "out_and_back": out_and_back_score,
        "repeated_circuit": repeated_circuit_score,
        "sinuous": sinuous_score,
    }

    main_keys = ("loop", "line", "out_and_back", "repeated_circuit")
    total = sum(raw[key] for key in main_keys)

    if total > 1e-9:
        for key in main_keys:
            raw[key] /= total

    return {
        "direct_ratio": direct_ratio,
        "compactness": compactness,
        "elongation": elongation,
        "span_m": span,
        "sharp_turn_ratio": sharp_turn_ratio,
        "medium_turn_ratio": medium_turn_ratio,
        "scores": raw,
    }


def _maximum_span_m(points):
    hull = _convex_hull(points)
    maximum = 0.0

    for index, first in enumerate(hull):
        for second in hull[index + 1:]:
            maximum = max(
                maximum,
                math.hypot(
                    second[0] - first[0],
                    second[1] - first[1],
                ),
            )

    return maximum


def _spatial_overlap_metrics(
    xy,
    radius_m=20.0,
    ignored_index_gap=8,
):
    radius_m = max(1.0, float(radius_m))
    cell_size = radius_m
    radius_squared = radius_m * radius_m
    cells = {}
    repeated_flags = [False] * len(xy)
    pass_counts = [1] * len(xy)

    for index, (x_value, y_value) in enumerate(xy):
        cell_x = math.floor(x_value / cell_size)
        cell_y = math.floor(y_value / cell_size)
        nearby_indices = []

        for offset_x in (-1, 0, 1):
            for offset_y in (-1, 0, 1):
                nearby_indices.extend(
                    cells.get(
                        (cell_x + offset_x, cell_y + offset_y),
                        (),
                    )
                )

        nonlocal_matches = 0

        for other_index in nearby_indices:
            if abs(index - other_index) <= ignored_index_gap:
                continue

            other_x, other_y = xy[other_index]
            distance_squared = (
                (x_value - other_x) ** 2
                + (y_value - other_y) ** 2
            )

            if distance_squared <= radius_squared:
                nonlocal_matches += 1
                repeated_flags[index] = True
                repeated_flags[other_index] = True

        pass_counts[index] += nonlocal_matches
        cells.setdefault((cell_x, cell_y), []).append(index)

    repeated_count = sum(repeated_flags)
    endpoint_allowance = min(
        repeated_count,
        max(2, int(round(len(xy) * 0.01))),
    )
    adjusted_repeated_count = max(
        0,
        repeated_count - endpoint_allowance,
    )

    return {
        "overlap_ratio": adjusted_repeated_count / max(1, len(xy)),
        "maximum_pass_count": max(pass_counts),
        "mean_pass_count": statistics.fmean(pass_counts),
    }


def _closure_index(total_distance, start_end_distance):
    return max(
        0.0,
        min(
            1.0,
            1.0
            - start_end_distance
            / max(50.0, total_distance * 0.10),
        ),
    )


def _occupation_metrics(
    xy,
    *,
    cell_size_m=25.0,
):
    """Mesure l'occupation spatiale réelle du parcours sur une grille."""
    cell_size_m = max(5.0, float(cell_size_m))
    visited = {}

    for x_value, y_value in xy:
        cell = (
            math.floor(x_value / cell_size_m),
            math.floor(y_value / cell_size_m),
        )
        visited[cell] = visited.get(cell, 0) + 1

    occupied_cells = len(visited)
    revisited_cells = sum(
        count > 1
        for count in visited.values()
    )
    maximum_cell_visits = max(
        visited.values(),
        default=0,
    )
    mean_cell_visits = (
        statistics.fmean(visited.values())
        if visited
        else 0.0
    )

    occupied_area_m2 = (
        occupied_cells
        * cell_size_m
        * cell_size_m
    )

    return {
        "cell_size_m": cell_size_m,
        "occupied_cells": occupied_cells,
        "revisited_cells": revisited_cells,
        "occupied_area_m2": occupied_area_m2,
        "revisited_cell_ratio": (
            revisited_cells / max(1, occupied_cells)
        ),
        "maximum_cell_visits": maximum_cell_visits,
        "mean_cell_visits": mean_cell_visits,
    }


def _radial_metrics(xy):
    if not xy:
        return {
            "radius_mean_m": 0.0,
            "radius_median_m": 0.0,
            "radius_max_m": 0.0,
        }

    center_x = statistics.fmean(
        point[0]
        for point in xy
    )
    center_y = statistics.fmean(
        point[1]
        for point in xy
    )

    radii = [
        math.hypot(
            point[0] - center_x,
            point[1] - center_y,
        )
        for point in xy
    ]

    return {
        "radius_mean_m": statistics.fmean(radii),
        "radius_median_m": statistics.median(radii),
        "radius_max_m": max(radii),
    }


def _dominant_orientation_degrees(xy):
    """Orientation principale de l'emprise, de 0° à 180°."""
    if len(xy) < 2:
        return 0.0

    mean_x = statistics.fmean(
        point[0]
        for point in xy
    )
    mean_y = statistics.fmean(
        point[1]
        for point in xy
    )

    xx = statistics.fmean(
        (point[0] - mean_x) ** 2
        for point in xy
    )
    yy = statistics.fmean(
        (point[1] - mean_y) ** 2
        for point in xy
    )
    xy_covariance = statistics.fmean(
        (point[0] - mean_x)
        * (point[1] - mean_y)
        for point in xy
    )

    angle = 0.5 * math.degrees(
        math.atan2(
            2.0 * xy_covariance,
            xx - yy,
        )
    )

    return angle % 180.0


def _occupation_class(
    *,
    occupied_area_m2,
    hull_area_m2,
    route_density_km_per_km2,
):
    occupation_ratio = (
        occupied_area_m2
        / max(1.0, hull_area_m2)
    )

    score = (
        min(1.0, occupation_ratio / 0.18) * 0.60
        + min(1.0, route_density_km_per_km2 / 3.0) * 0.40
    )

    if score >= 0.85:
        label = "très compacte"
    elif score >= 0.65:
        label = "compacte"
    elif score >= 0.42:
        label = "normale"
    elif score >= 0.22:
        label = "étendue"
    else:
        label = "très étendue"

    return score, label


def _recommended_terrain_size(
    width_m,
    height_m,
    maximum_span_m,
):
    margin = max(
        750.0,
        maximum_span_m * 0.18,
    )

    recommended_width = width_m + 2.0 * margin
    recommended_height = height_m + 2.0 * margin

    def round_up_km(value_m):
        return math.ceil(
            value_m / 1000.0
        )

    return {
        "terrain_width_km": round_up_km(
            recommended_width
        ),
        "terrain_height_km": round_up_km(
            recommended_height
        ),
        "terrain_margin_m": margin,
    }


def _relief_index(
    *,
    distance_km,
    elevation_gain_m,
    altitude_amplitude_m,
    grade_median_percent,
    grade_max_percent,
):
    gain_per_km = (
        elevation_gain_m
        / max(distance_km, 0.1)
    )

    score = (
        min(1.0, gain_per_km / 80.0) * 0.35
        + min(1.0, altitude_amplitude_m / 1200.0) * 0.25
        + min(1.0, grade_median_percent / 10.0) * 0.25
        + min(1.0, grade_max_percent / 35.0) * 0.15
    )

    if score >= 0.82:
        label = "très fort"
    elif score >= 0.62:
        label = "fort"
    elif score >= 0.42:
        label = "soutenu"
    elif score >= 0.22:
        label = "modéré"
    else:
        label = "faible"

    return score, label


def analyze_gpx(gpx_file):
    gpx_file = Path(gpx_file)
    points = _read_points(gpx_file)

    segments = [
        _distance_m(points[index - 1], points[index])
        for index in range(1, len(points))
    ]

    total_distance = sum(segments)
    start_end = _distance_m(points[0], points[-1])

    xy = _local_xy(points)
    xs = [point[0] for point in xy]
    ys = [point[1] for point in xy]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    bbox_area = width * height
    hull = _convex_hull(xy)
    hull_area = _polygon_area(hull)
    maximum_span = _maximum_span_m(hull)
    turn_angles = _turn_angles_degrees(xy)

    overlap_10 = _spatial_overlap_metrics(xy, radius_m=10.0)
    overlap_20 = _spatial_overlap_metrics(xy, radius_m=20.0)
    overlap_40 = _spatial_overlap_metrics(xy, radius_m=40.0)

    closure_index = _closure_index(total_distance, start_end)
    linearity_index = min(
        1.0,
        start_end / max(total_distance, 1.0),
    )
    overlap_index = min(
        1.0,
        overlap_20["overlap_ratio"] * 1.20
        + overlap_40["overlap_ratio"] * 0.35,
    )
    repetition_index = min(
        1.0,
        overlap_index * 0.75
        + min(
            1.0,
            max(
                0.0,
                overlap_20["mean_pass_count"] - 1.0,
            )
            / 1.5,
        )
        * 0.20
        + min(
            1.0,
            overlap_20["overlap_ratio"] / 0.35,
        )
        * 0.05,
    )
    footprint_fill = hull_area / max(bbox_area, 1.0)
    spatial_density = (
        total_distance / max(1.0, math.sqrt(max(hull_area, 1.0)))
    )
    compactness_index = min(
        1.0,
        footprint_fill * 0.65
        + min(1.0, spatial_density / 8.0) * 0.35,
    )

    occupation_25 = _occupation_metrics(
        xy,
        cell_size_m=25.0,
    )
    occupation_50 = _occupation_metrics(
        xy,
        cell_size_m=50.0,
    )
    radial = _radial_metrics(xy)
    dominant_orientation = _dominant_orientation_degrees(xy)

    route_density_km_per_km2 = (
        total_distance / 1000.0
        / max(hull_area / 1_000_000.0, 0.001)
    )

    occupation_score, occupation_label = _occupation_class(
        occupied_area_m2=occupation_25["occupied_area_m2"],
        hull_area_m2=hull_area,
        route_density_km_per_km2=route_density_km_per_km2,
    )

    span_distance_ratio = (
        maximum_span
        / max(total_distance, 1.0)
    )

    if closure_index >= 0.80 and span_distance_ratio <= 0.35:
        footprint_level = "compacte"
    elif span_distance_ratio <= 0.48:
        footprint_level = "modérée"
    elif span_distance_ratio <= 0.70:
        footprint_level = "étendue"
    else:
        footprint_level = "très étendue"

    terrain_size = _recommended_terrain_size(
        width_m=width,
        height_m=height,
        maximum_span_m=maximum_span,
    )

    mean_spacing = statistics.fmean(segments)
    geometry_confidence = min(
        1.0,
        max(0.4, 30.0 / max(30.0, mean_spacing))
        * max(0.6, min(1.0, len(points) / 500.0)),
    )

    elevations = [point[2] for point in points]
    relief_available = all(value is not None for value in elevations)

    result = {
        "source_file": str(gpx_file),
        "point_count": len(points),
        "distance_total_km": total_distance / 1000.0,
        "distance_start_end_km": start_end / 1000.0,
        "start_end_ratio": start_end / max(total_distance, 1.0),
        "footprint_width_km": width / 1000.0,
        "footprint_height_km": height / 1000.0,
        "footprint_bbox_area_km2": bbox_area / 1_000_000.0,
        "footprint_hull_area_km2": hull_area / 1_000_000.0,
        "footprint_fill_ratio": footprint_fill,
        "footprint_max_span_km": maximum_span / 1000.0,
        "footprint_elongation_ratio": (
            max(width, height) / max(min(width, height), 1.0)
        ),
        "route_density_km_per_km2": route_density_km_per_km2,
        "turn_angle_mean_deg": (
            statistics.fmean(turn_angles) if turn_angles else 0.0
        ),
        "turn_angle_median_deg": (
            statistics.median(turn_angles) if turn_angles else 0.0
        ),
        "sharp_turn_ratio_percent": (
            sum(angle >= 120.0 for angle in turn_angles)
            / max(1, len(turn_angles))
            * 100.0
        ),
        "medium_turn_ratio_percent": (
            sum(angle >= 60.0 for angle in turn_angles)
            / max(1, len(turn_angles))
            * 100.0
        ),
        "overlap_10m_percent": overlap_10["overlap_ratio"] * 100.0,
        "overlap_20m_percent": overlap_20["overlap_ratio"] * 100.0,
        "overlap_40m_percent": overlap_40["overlap_ratio"] * 100.0,
        "maximum_pass_count_20m": overlap_20["maximum_pass_count"],
        "mean_pass_count_20m": overlap_20["mean_pass_count"],
        "closure_index_percent": closure_index * 100.0,
        "overlap_index_percent": overlap_index * 100.0,
        "repetition_index_percent": repetition_index * 100.0,
        "linearity_index_percent": linearity_index * 100.0,
        "compactness_index_percent": compactness_index * 100.0,
        "occupied_area_25m_km2": (
            occupation_25["occupied_area_m2"]
            / 1_000_000.0
        ),
        "occupied_cells_25m": occupation_25["occupied_cells"],
        "revisited_cells_25m_percent": (
            occupation_25["revisited_cell_ratio"]
            * 100.0
        ),
        "maximum_cell_visits_25m": (
            occupation_25["maximum_cell_visits"]
        ),
        "mean_cell_visits_25m": (
            occupation_25["mean_cell_visits"]
        ),
        "occupied_area_50m_km2": (
            occupation_50["occupied_area_m2"]
            / 1_000_000.0
        ),
        "radius_mean_km": radial["radius_mean_m"] / 1000.0,
        "radius_median_km": radial["radius_median_m"] / 1000.0,
        "radius_max_km": radial["radius_max_m"] / 1000.0,
        "dominant_orientation_deg": dominant_orientation,
        "occupation_index_percent": occupation_score * 100.0,
        "occupation_level": occupation_label,
        "span_distance_ratio": span_distance_ratio,
        "footprint_level": footprint_level,
        "recommended_terrain_width_km": (
            terrain_size["terrain_width_km"]
        ),
        "recommended_terrain_height_km": (
            terrain_size["terrain_height_km"]
        ),
        "recommended_terrain_margin_m": (
            terrain_size["terrain_margin_m"]
        ),
        "spacing_mean_m": mean_spacing,
        "spacing_median_m": statistics.median(segments),
        "spacing_min_m": min(segments),
        "spacing_max_m": max(segments),
        "point_density_per_km": len(points) / max(total_distance / 1000.0, 0.001),
        "center_latitude": statistics.fmean(point[0] for point in points),
        "center_longitude": statistics.fmean(point[1] for point in points),
        "geometry_confidence_percent": geometry_confidence * 100.0,
        "elevation_completeness_percent": (
            sum(value is not None for value in elevations) / len(elevations) * 100.0
        ),
    }

    if relief_available:
        smoothed = _median_smooth([float(value) for value in elevations])
        gain = 0.0
        loss = 0.0
        grades = []

        for index, distance in enumerate(segments, start=1):
            difference = smoothed[index] - smoothed[index - 1]
            gain += max(0.0, difference)
            loss += max(0.0, -difference)

            if distance >= 2.0:
                grades.append(abs(difference / distance) * 100.0)

        grade_mean = statistics.fmean(grades) if grades else 0.0
        grade_median = statistics.median(grades) if grades else 0.0
        grade_maximum = max(grades) if grades else 0.0
        altitude_amplitude = max(smoothed) - min(smoothed)

        relief_score, relief_label = _relief_index(
            distance_km=total_distance / 1000.0,
            elevation_gain_m=gain,
            altitude_amplitude_m=altitude_amplitude,
            grade_median_percent=grade_median,
            grade_max_percent=grade_maximum,
        )

        result.update(
            {
                "altitude_min_m": min(smoothed),
                "altitude_max_m": max(smoothed),
                "altitude_amplitude_m": altitude_amplitude,
                "elevation_gain_m": gain,
                "elevation_loss_m": loss,
                "grade_mean_percent": grade_mean,
                "grade_median_percent": grade_median,
                "grade_max_percent": grade_maximum,
                "relief_index_percent": relief_score * 100.0,
                "relief_level": relief_label,
                "relief_confidence_percent": geometry_confidence * 100.0,
            }
        )
    else:
        result.update(
            {
                "altitude_min_m": None,
                "altitude_max_m": None,
                "altitude_amplitude_m": None,
                "elevation_gain_m": None,
                "elevation_loss_m": None,
                "grade_mean_percent": None,
                "grade_median_percent": None,
                "grade_max_percent": None,
                "relief_index_percent": None,
                "relief_level": "indisponible",
                "relief_confidence_percent": 0.0,
            }
        )

    return result
