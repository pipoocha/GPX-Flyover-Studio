from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from studio.config.loader import ProjectLoaderV5
from studio.geometry.path_builder import PathBuilder
from studio.io.gpx_loader import GPXLoader
from studio.terrain.copernicus_grid import CopernicusGridBuilder
from studio.terrain.srtm_grid import SRTMGridBuilder
from studio.terrain.terrain_sampler import TerrainSampler


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diagnostic d'alignement GPX / terrain."
    )
    parser.add_argument(
        "project",
        nargs="?",
        default="projects/project_v5.yaml",
        help="Chemin du projet YAML.",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=0,
        help="Nombre maximal de points à contrôler. 0 = tous.",
    )
    return parser


def build_terrain(project):
    source = project.terrain.source.lower()

    if source == "srtm":
        print("Création terrain SRTM...")
        builder = SRTMGridBuilder(
            project.points,
            resolution=0.0005,
        )
    elif source == "copernicus":
        print("Création terrain Copernicus GLO-30...")
        builder = CopernicusGridBuilder(
            project.points,
            margin=project.terrain.margin,
            cache_dir=getattr(
                config,
                "COPERNICUS_CACHE_DIR",
                "cache/dem/copernicus_glo30",
            ),
            max_cells=project.terrain.max_cells,
        )
    else:
        raise ValueError(f"Source terrain inconnue : {source}")

    grid = builder.build()
    sampler = TerrainSampler(grid)
    return builder, grid, sampler


def sample_path(path_coords, maximum):
    if maximum <= 0 or len(path_coords) <= maximum:
        return path_coords

    indices = np.linspace(
        0,
        len(path_coords) - 1,
        maximum,
        dtype=int,
    )
    return path_coords[indices]


def calculate_statistics(path_coords, sampler, expected_offset):
    sampled = np.asarray(path_coords, dtype=float)
    errors = []
    outside = 0

    x_axis = np.asarray(np.mean(sampler.grid.x, axis=0), dtype=float)
    y_axis = np.asarray(np.mean(sampler.grid.y, axis=1), dtype=float)

    x_min = float(np.min(x_axis))
    x_max = float(np.max(x_axis))
    y_min = float(np.min(y_axis))
    y_max = float(np.max(y_axis))

    for point in sampled:
        x, y, z = map(float, point[:3])

        if not (x_min <= x <= x_max and y_min <= y <= y_max):
            outside += 1
            continue

        terrain_z = sampler.height(x, y)
        actual_offset = z - terrain_z
        errors.append(abs(actual_offset - float(expected_offset)))

    if errors:
        mean_error = float(np.mean(errors))
        max_error = float(np.max(errors))
    else:
        mean_error = float("nan")
        max_error = float("nan")

    return {
        "checked": len(sampled),
        "valid": len(errors),
        "outside": outside,
        "mean_error": mean_error,
        "max_error": max_error,
    }


def verdict(statistics):
    if statistics["valid"] == 0:
        return "ERREUR"
    if statistics["outside"] > 0:
        return "ATTENTION"
    if statistics["max_error"] <= 0.25:
        return "OK"
    if statistics["max_error"] <= 2.0:
        return "ATTENTION"
    return "ERREUR"


def main() -> int:
    args = build_argument_parser().parse_args()

    project_file = Path(args.project)
    if not project_file.is_absolute():
        project_file = ROOT / project_file

    project = ProjectLoaderV5(project_file).load(require_existing_gpx=True)

    print()
    print("Lecture GPX...")
    project.points = GPXLoader(project.gpx.file).load()

    if len(project.points) < 2:
        raise ValueError("Le GPX contient moins de deux points.")

    builder, grid, sampler = build_terrain(project)

    projection = builder.projection
    origin_x = float(builder.origin_x)
    origin_y = float(builder.origin_y)

    print("Construction trajectoire...")

    path_coords = PathBuilder(
        project.points,
        origin_x=origin_x,
        origin_y=origin_y,
        sampler=sampler,
        projection=projection,
        z_offset=project.track.z_offset,
    ).build()

    checked_path = sample_path(path_coords, args.max_points)
    statistics = calculate_statistics(
        checked_path,
        sampler,
        project.track.z_offset,
    )
    status = verdict(statistics)

    print()
    print("===================================")
    print("DIAGNOSTIC TRACE / TERRAIN")
    print("-----------------------------------")
    print(f"Projet             : {project_file}")
    print(f"GPX                : {project.gpx.file}")
    print(f"Source terrain     : {project.terrain.source}")
    print(f"Projection EPSG    : {projection.epsg}")
    print(f"Origine locale     : {origin_x:.3f}, {origin_y:.3f}")
    print(f"Grille terrain     : {grid.x.shape[1]} x {grid.x.shape[0]}")
    print(f"Points GPX         : {len(project.points)}")
    print(f"Points trajectoire : {len(path_coords)}")
    print(f"Points contrôlés   : {statistics['checked']}")
    print(f"Points hors DEM    : {statistics['outside']}")

    if statistics["valid"] > 0:
        print(f"Erreur Z moyenne   : {statistics['mean_error']:.3f} m")
        print(f"Erreur Z maximale  : {statistics['max_error']:.3f} m")
    else:
        print("Erreur Z moyenne   : indisponible")
        print("Erreur Z maximale  : indisponible")

    print(f"Trace / relief     : {status}")
    print("===================================")
    print()

    return 0 if status == "OK" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print()
        print("ERREUR :", error)
        raise
