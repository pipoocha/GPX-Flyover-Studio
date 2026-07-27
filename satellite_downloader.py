from __future__ import annotations

import argparse
import io
import json
import math
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from PIL import Image, ImageDraw


TILE_SIZE = 256
DEFAULT_ZOOM = 14
DEFAULT_MARGIN_RATIO = 0.08
DEFAULT_PREVIEW_MAX_SIZE = 2048
DEFAULT_VIDEO_MAX_SIZE = 4096

ESRI_WORLD_IMAGERY = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)


def read_gpx_points(gpx_file: Path) -> list[tuple[float, float]]:
    root = ET.parse(gpx_file).getroot()
    points: list[tuple[float, float]] = []

    for element in root.iter():
        if element.tag.endswith("trkpt"):
            latitude = float(element.attrib["lat"])
            longitude = float(element.attrib["lon"])
            points.append((latitude, longitude))

    if len(points) < 2:
        raise ValueError("Le GPX ne contient pas assez de points.")

    return points


def expand_bounds(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    margin_ratio: float,
) -> tuple[float, float, float, float]:
    lat_margin = max((max_lat - min_lat) * margin_ratio, 0.002)
    lon_margin = max((max_lon - min_lon) * margin_ratio, 0.002)

    return (
        min_lat - lat_margin,
        min_lon - lon_margin,
        max_lat + lat_margin,
        max_lon + lon_margin,
    )


def lon_to_tile_x(longitude: float, zoom: int) -> float:
    return (longitude + 180.0) / 360.0 * (2**zoom)


def lat_to_tile_y(latitude: float, zoom: int) -> float:
    latitude = max(-85.05112878, min(85.05112878, latitude))
    lat_radians = math.radians(latitude)

    return (
        1.0
        - math.asinh(math.tan(lat_radians)) / math.pi
    ) / 2.0 * (2**zoom)


def tile_x_to_lon(tile_x: float, zoom: int) -> float:
    return tile_x / (2**zoom) * 360.0 - 180.0


def tile_y_to_lat(tile_y: float, zoom: int) -> float:
    mercator_y = math.pi * (1.0 - 2.0 * tile_y / (2**zoom))
    return math.degrees(math.atan(math.sinh(mercator_y)))


def download_tile(
    session: requests.Session,
    zoom: int,
    tile_x: int,
    tile_y: int,
    retries: int = 3,
) -> Image.Image:
    url = ESRI_WORLD_IMAGERY.format(
        z=zoom,
        x=tile_x,
        y=tile_y,
    )

    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            response = session.get(
                url,
                timeout=30,
                headers={
                    "User-Agent": (
                        "GPX-Flyover-Studio/1.0 "
                        "(personal visualization project)"
                    )
                },
            )
            response.raise_for_status()

            image = Image.open(
                io.BytesIO(response.content)
            ).convert("RGB")

            if image.size != (TILE_SIZE, TILE_SIZE):
                image = image.resize((TILE_SIZE, TILE_SIZE))

            return image

        except Exception as error:
            last_error = error
            time.sleep(1.0 + attempt)

    raise RuntimeError(
        f"Impossible de télécharger la tuile "
        f"z={zoom}, x={tile_x}, y={tile_y}: {last_error}"
    )


def resized_copy(image: Image.Image, maximum_size: int) -> Image.Image:
    maximum_size = max(256, int(maximum_size))
    if max(image.size) <= maximum_size:
        return image.copy()
    resized = image.copy()
    resized.thumbnail((maximum_size, maximum_size), Image.Resampling.LANCZOS)
    return resized


def save_optimized_texture(
    image: Image.Image,
    output_file: Path,
    maximum_size: int,
) -> tuple[int, int]:
    optimized = resized_copy(image, maximum_size)
    optimized.save(output_file, format="PNG", optimize=True, compress_level=6)
    size = optimized.size
    optimized.close()
    return size


def create_mosaic(
    gpx_file: Path,
    zoom: int,
    margin_ratio: float,
    cache_dir: Path,
    output_dir: Path,
    preview_max_size: int = DEFAULT_PREVIEW_MAX_SIZE,
    video_max_size: int = DEFAULT_VIDEO_MAX_SIZE,
) -> tuple[Path, Path, Path]:
    points = read_gpx_points(gpx_file)

    latitudes = [point[0] for point in points]
    longitudes = [point[1] for point in points]

    min_lat, min_lon, max_lat, max_lon = expand_bounds(
        min(latitudes),
        min(longitudes),
        max(latitudes),
        max(longitudes),
        margin_ratio,
    )

    x_min_float = lon_to_tile_x(min_lon, zoom)
    x_max_float = lon_to_tile_x(max_lon, zoom)
    y_min_float = lat_to_tile_y(max_lat, zoom)
    y_max_float = lat_to_tile_y(min_lat, zoom)

    x_min = math.floor(x_min_float)
    x_max = math.floor(x_max_float)
    y_min = math.floor(y_min_float)
    y_max = math.floor(y_max_float)

    tile_columns = x_max - x_min + 1
    tile_rows = y_max - y_min + 1

    print("===================================")
    print("SATELLITE DOWNLOADER")
    print("GPX        :", gpx_file)
    print("Points     :", len(points))
    print("Zoom       :", zoom)
    print("Tuiles     :", f"{tile_columns} x {tile_rows}")
    print("Total      :", tile_columns * tile_rows)
    print("===================================")

    mosaic = Image.new(
        "RGB",
        (
            tile_columns * TILE_SIZE,
            tile_rows * TILE_SIZE,
        ),
    )

    cache_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        tile_number = 0
        total_tiles = tile_columns * tile_rows

        for tile_y in range(y_min, y_max + 1):
            for tile_x in range(x_min, x_max + 1):
                tile_number += 1

                tile_cache = (
                    cache_dir
                    / f"z{zoom}_{tile_x}_{tile_y}.jpg"
                )

                if tile_cache.exists():
                    tile = Image.open(tile_cache).convert("RGB")
                else:
                    tile = download_tile(
                        session=session,
                        zoom=zoom,
                        tile_x=tile_x,
                        tile_y=tile_y,
                    )
                    tile.save(tile_cache, quality=92)

                paste_x = (tile_x - x_min) * TILE_SIZE
                paste_y = (tile_y - y_min) * TILE_SIZE
                mosaic.paste(tile, (paste_x, paste_y))

                print(
                    f"\rTuile {tile_number}/{total_tiles}",
                    end="",
                    flush=True,
                )

    print()

    west = tile_x_to_lon(x_min, zoom)
    east = tile_x_to_lon(x_max + 1, zoom)
    north = tile_y_to_lat(y_min, zoom)
    south = tile_y_to_lat(y_max + 1, zoom)

    stem = gpx_file.stem
    mosaic_file = output_dir / f"{stem}_satellite_z{zoom}.png"
    metadata_file = output_dir / f"{stem}_satellite_z{zoom}.json"
    preview_file = output_dir / f"{stem}_satellite_preview_z{zoom}.png"
    preview_texture_file = output_dir / f"{stem}_satellite_z{zoom}_preview.png"
    video_texture_file = output_dir / f"{stem}_satellite_z{zoom}_video.png"

    mosaic.save(mosaic_file, format="PNG", optimize=True, compress_level=6)
    preview_texture_size = save_optimized_texture(
        mosaic, preview_texture_file, preview_max_size
    )
    video_texture_size = save_optimized_texture(
        mosaic, video_texture_file, video_max_size
    )

    metadata = {
        "source": "Esri World Imagery",
        "zoom": zoom,
        "image_width": mosaic.width,
        "image_height": mosaic.height,
        "optimized_textures": {
            "preview": {
                "file": preview_texture_file.name,
                "width": preview_texture_size[0],
                "height": preview_texture_size[1],
                "maximum_size": int(preview_max_size),
            },
            "video": {
                "file": video_texture_file.name,
                "width": video_texture_size[0],
                "height": video_texture_size[1],
                "maximum_size": int(video_max_size),
            },
        },
        "tile_bounds": {
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
        },
        "geographic_bounds_wgs84": {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
        },
        "gpx_bounds_wgs84": {
            "west": min(longitudes),
            "south": min(latitudes),
            "east": max(longitudes),
            "north": max(latitudes),
        },
    }

    metadata_file.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    preview = mosaic.copy()
    draw = ImageDraw.Draw(preview)

    track_pixels: list[tuple[float, float]] = []

    for latitude, longitude in points:
        world_x = lon_to_tile_x(longitude, zoom)
        world_y = lat_to_tile_y(latitude, zoom)

        pixel_x = (world_x - x_min) * TILE_SIZE
        pixel_y = (world_y - y_min) * TILE_SIZE
        track_pixels.append((pixel_x, pixel_y))

    if len(track_pixels) >= 2:
        draw.line(
            track_pixels,
            fill=(252, 76, 2),
            width=6,
            joint="curve",
        )

        start_x, start_y = track_pixels[0]
        end_x, end_y = track_pixels[-1]

        radius = 10
        draw.ellipse(
            (
                start_x - radius,
                start_y - radius,
                start_x + radius,
                start_y + radius,
            ),
            fill=(0, 220, 80),
        )
        draw.ellipse(
            (
                end_x - radius,
                end_y - radius,
                end_x + radius,
                end_y + radius,
            ),
            fill=(230, 40, 40),
        )

    preview.save(preview_file)

    print("Mosaïque originale :", mosaic_file)
    print(
        "Texture preview :",
        preview_texture_file,
        f"{preview_texture_size[0]} x {preview_texture_size[1]}",
    )
    print(
        "Texture vidéo :",
        video_texture_file,
        f"{video_texture_size[0]} x {video_texture_size[1]}",
    )
    print("Métadonnées :", metadata_file)
    print("Aperçu GPX :", preview_file)

    return mosaic_file, metadata_file, preview_file


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Télécharge une mosaïque satellite Esri "
            "pour l'emprise d'un fichier GPX."
        )
    )

    parser.add_argument(
        "gpx_file",
        type=Path,
        help="Chemin du fichier GPX.",
    )

    parser.add_argument(
        "--zoom",
        type=int,
        default=DEFAULT_ZOOM,
        help="Niveau de zoom, 14 par défaut.",
    )

    parser.add_argument(
        "--margin",
        type=float,
        default=DEFAULT_MARGIN_RATIO,
        help="Marge autour du GPX, 0.08 par défaut.",
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("cache/satellite/tiles"),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("cache/satellite"),
    )

    parser.add_argument(
        "--preview-max-size",
        type=int,
        default=DEFAULT_PREVIEW_MAX_SIZE,
        help="Dimension maximale de la texture de preview.",
    )

    parser.add_argument(
        "--video-max-size",
        type=int,
        default=DEFAULT_VIDEO_MAX_SIZE,
        help="Dimension maximale de la texture vidéo.",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    if not arguments.gpx_file.exists():
        raise FileNotFoundError(
            f"GPX introuvable : {arguments.gpx_file}"
        )

    create_mosaic(
        gpx_file=arguments.gpx_file,
        zoom=arguments.zoom,
        margin_ratio=arguments.margin,
        cache_dir=arguments.cache_dir,
        output_dir=arguments.output_dir,
        preview_max_size=arguments.preview_max_size,
        video_max_size=arguments.video_max_size,
    )


if __name__ == "__main__":
    main()
