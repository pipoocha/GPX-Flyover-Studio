from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image

from studio.geometry.path_builder import PathBuilder
from studio.io.gpx_loader import GPXLoader
from studio.scene.track import Track
from studio.terrain.srtm_grid import SRTMGridBuilder
from studio.terrain.terrain_mesh import TerrainMesh
from studio.terrain.terrain_sampler import TerrainSampler


DEFAULT_GPX = Path("gpx/31_kagbeni_sangda.gpx")
DEFAULT_ZOOM = 14
SATELLITE_DIR = Path("cache/satellite")
TEMP_TEXTURE_DIR = Path("cache/satellite/cropped")


def read_gpx_bounds(gpx_file: Path):
    root = ET.parse(gpx_file).getroot()
    lats, lons = [], []

    for element in root.iter():
        if element.tag.endswith("trkpt"):
            lats.append(float(element.attrib["lat"]))
            lons.append(float(element.attrib["lon"]))

    if len(lats) < 2:
        raise ValueError("Le GPX ne contient pas assez de points.")

    return min(lons), min(lats), max(lons), max(lats)


def satellite_files(gpx_file: Path, zoom: int):
    stem = gpx_file.stem
    return (
        SATELLITE_DIR / f"{stem}_satellite_z{zoom}.png",
        SATELLITE_DIR / f"{stem}_satellite_z{zoom}.json",
    )


def ensure_satellite_exists(gpx_file: Path, zoom: int):
    image_file, metadata_file = satellite_files(gpx_file, zoom)

    if image_file.exists() and metadata_file.exists():
        return image_file, metadata_file

    downloader = Path("satellite_downloader.py")
    if not downloader.exists():
        raise FileNotFoundError(
            "La mosaïque satellite n'existe pas et satellite_downloader.py est introuvable."
        )

    subprocess.run(
        [
            sys.executable,
            str(downloader),
            str(gpx_file),
            "--zoom",
            str(zoom),
        ],
        check=True,
    )

    if not image_file.exists() or not metadata_file.exists():
        raise FileNotFoundError("Les fichiers satellite attendus sont absents.")

    return image_file, metadata_file


def geographic_to_pixel(longitude, latitude, west, south, east, north, width, height):
    x_ratio = (longitude - west) / max(1e-12, east - west)
    y_ratio = (north - latitude) / max(1e-12, north - south)
    return x_ratio * width, y_ratio * height


def crop_texture_to_gpx(
    gpx_file: Path,
    image_file: Path,
    metadata_file: Path,
    margin_ratio: float,
):
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    bounds = metadata["geographic_bounds_wgs84"]

    west = float(bounds["west"])
    south = float(bounds["south"])
    east = float(bounds["east"])
    north = float(bounds["north"])

    gpx_west, gpx_south, gpx_east, gpx_north = read_gpx_bounds(gpx_file)

    lon_margin = max((gpx_east - gpx_west) * margin_ratio, 0.001)
    lat_margin = max((gpx_north - gpx_south) * margin_ratio, 0.001)

    crop_west = max(west, gpx_west - lon_margin)
    crop_east = min(east, gpx_east + lon_margin)
    crop_south = max(south, gpx_south - lat_margin)
    crop_north = min(north, gpx_north + lat_margin)

    image = Image.open(image_file).convert("RGB")

    left, top = geographic_to_pixel(
        crop_west, crop_north, west, south, east, north, image.width, image.height
    )
    right, bottom = geographic_to_pixel(
        crop_east, crop_south, west, south, east, north, image.width, image.height
    )

    box = (
        max(0, int(round(left))),
        max(0, int(round(top))),
        min(image.width, int(round(right))),
        min(image.height, int(round(bottom))),
    )

    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("Découpage satellite invalide.")

    cropped = image.crop(box)

    TEMP_TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    output_file = TEMP_TEXTURE_DIR / f"{gpx_file.stem}_terrain_texture.png"
    cropped.save(output_file)

    print("Texture terrain :", output_file)
    print("Dimensions      :", cropped.size)

    return output_file


def build_terrain_and_path(gpx_file: Path):
    print("Lecture GPX...")
    points = GPXLoader(gpx_file).load()
    print(f"{len(points)} points chargés")

    print("Construction SRTM...")
    builder = SRTMGridBuilder(points, resolution=0.0005)
    grid = builder.build()

    mesh = TerrainMesh(grid).build()
    sampler = TerrainSampler(grid)

    path_coords = PathBuilder(
        points,
        origin_x=builder.origin_x,
        origin_y=builder.origin_y,
        sampler=sampler,
        z_offset=60,
    ).build()

    return mesh, path_coords


def create_viewer(mesh, path_coords, texture_file: Path, flip_vertical: bool):
    texture = pv.read_texture(str(texture_file))

    if flip_vertical:
        texture.flip_y()

    plotter = pv.Plotter(window_size=(1280, 720))
    plotter.set_background("black")

    plotter.add_mesh(
        mesh,
        texture=texture,
        smooth_shading=True,
        ambient=0.62,
        diffuse=0.72,
        specular=0.03,
    )

    track_mesh = Track(path_coords, radius=10, sides=12).to_mesh()
    plotter.add_mesh(track_mesh, color="#FC4C02", smooth_shading=True)

    start = np.asarray(path_coords[0], dtype=float)
    finish = np.asarray(path_coords[-1], dtype=float)

    plotter.add_mesh(pv.Sphere(radius=28, center=start), color="lime")
    plotter.add_mesh(pv.Sphere(radius=28, center=finish), color="red")

    plotter.add_light(
        pv.Light(
            position=(3000, -5000, 7000),
            focal_point=(0, 0, 0),
            intensity=0.75,
        )
    )

    plotter.add_text(
        "Satellite 3D — souris : rotation / molette : zoom",
        font_size=14,
    )

    plotter.reset_camera()
    plotter.camera.zoom(1.15)
    plotter.show()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Visualiseur autonome : relief SRTM, satellite et trace GPX."
    )
    parser.add_argument("gpx_file", nargs="?", type=Path, default=DEFAULT_GPX)
    parser.add_argument("--zoom", type=int, default=DEFAULT_ZOOM)
    parser.add_argument("--no-flip", action="store_true")
    parser.add_argument("--margin", type=float, default=0.06)
    return parser.parse_args()


def main():
    arguments = parse_arguments()

    if not arguments.gpx_file.exists():
        raise FileNotFoundError(f"GPX introuvable : {arguments.gpx_file}")

    image_file, metadata_file = ensure_satellite_exists(
        arguments.gpx_file,
        arguments.zoom,
    )

    texture_file = crop_texture_to_gpx(
        gpx_file=arguments.gpx_file,
        image_file=image_file,
        metadata_file=metadata_file,
        margin_ratio=arguments.margin,
    )

    mesh, path_coords = build_terrain_and_path(arguments.gpx_file)

    create_viewer(
        mesh=mesh,
        path_coords=path_coords,
        texture_file=texture_file,
        flip_vertical=not arguments.no_flip,
    )


if __name__ == "__main__":
    main()
