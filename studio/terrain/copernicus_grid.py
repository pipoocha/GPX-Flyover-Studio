from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.merge import merge
from rasterio.enums import Resampling

from studio.terrain.projection import Projection
from studio.terrain.terrain_extent import TerrainExtent
from studio.terrain.terrain_grid import TerrainGrid


class CopernicusGridBuilder:
    """
    Construit directement le terrain depuis Copernicus DEM GLO-30.

    - téléchargement automatique des tuiles publiques AWS ;
    - découpage à l'emprise du GPX ;
    - conservation du relief natif ;
    - suppression des valeurs NoData ;
    - réduction automatique de la grille si elle est trop lourde.
    """

    BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"

    def __init__(
        self,
        points,
        margin=0.02,
        cache_dir="cache/dem/copernicus_glo30",
        max_cells=220_000,
    ):
        self.points = points
        self.margin = float(margin)
        self.cache_dir = Path(cache_dir)
        self.max_cells = max(10_000, int(max_cells))

        self.origin_x = 0.0
        self.origin_y = 0.0
        self.projection = Projection(self.points)

    @staticmethod
    def tile_name(latitude: int, longitude: int) -> str:
        northing = (
            f"N{latitude:02d}_00"
            if latitude >= 0
            else f"S{abs(latitude):02d}_00"
        )

        easting = (
            f"E{longitude:03d}_00"
            if longitude >= 0
            else f"W{abs(longitude):03d}_00"
        )

        return (
            "Copernicus_DSM_COG_10_"
            f"{northing}_{easting}_DEM"
        )

    @staticmethod
    def required_tiles(extent) -> list[tuple[int, int]]:
        latitude_start = math.floor(extent.south)
        latitude_end = math.ceil(extent.north)

        longitude_start = math.floor(extent.west)
        longitude_end = math.ceil(extent.east)

        tiles = []

        for latitude in range(latitude_start, latitude_end):
            for longitude in range(longitude_start, longitude_end):
                tiles.append((latitude, longitude))

        return tiles

    def download_tile(
        self,
        latitude: int,
        longitude: int,
    ) -> Path:
        tile = self.tile_name(
            latitude,
            longitude,
        )

        tile_dir = self.cache_dir / tile
        output_file = tile_dir / f"{tile}.tif"

        if output_file.exists():
            print("DEM en cache :", output_file.name)
            return output_file

        tile_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        url = (
            f"{self.BASE_URL}/"
            f"{tile}/"
            f"{tile}.tif"
        )

        print("Téléchargement DEM :", tile)

        with requests.get(
            url,
            stream=True,
            timeout=120,
            headers={
                "User-Agent": (
                    "GPX-Flyover-Studio/1.0 "
                    "(personal visualization project)"
                )
            },
        ) as response:
            if response.status_code == 404:
                raise FileNotFoundError(
                    "Tuile Copernicus GLO-30 non disponible : "
                    f"{tile}"
                )

            response.raise_for_status()

            temporary_file = output_file.with_suffix(
                ".tif.part"
            )

            with open(
                temporary_file,
                "wb",
            ) as file:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        file.write(chunk)

            temporary_file.replace(
                output_file
            )

        return output_file

    @staticmethod
    def fill_invalid_values(
        elevations: np.ndarray,
    ) -> np.ndarray:
        z = np.asarray(
            elevations,
            dtype=float,
        ).copy()

        invalid = (
            ~np.isfinite(z)
            | (z < -500.0)
            | (z > 10_000.0)
        )

        if not invalid.any():
            return z

        z[invalid] = np.nan

        for _ in range(12):
            missing = np.isnan(z)

            if not missing.any():
                break

            padded = np.pad(
                z,
                1,
                mode="edge",
            )

            neighbours = [
                padded[:-2, 1:-1],
                padded[2:, 1:-1],
                padded[1:-1, :-2],
                padded[1:-1, 2:],
                padded[:-2, :-2],
                padded[:-2, 2:],
                padded[2:, :-2],
                padded[2:, 2:],
            ]

            stack = np.stack(
                neighbours,
                axis=0,
            )

            with np.errstate(
                invalid="ignore",
            ):
                replacement = np.nanmean(
                    stack,
                    axis=0,
                )

            can_fill = (
                missing
                & np.isfinite(replacement)
            )

            z[can_fill] = replacement[can_fill]

        if np.isnan(z).any():
            valid_values = z[
                np.isfinite(z)
            ]

            fallback = (
                float(np.median(valid_values))
                if valid_values.size
                else 0.0
            )

            z[
                ~np.isfinite(z)
            ] = fallback

        return z

    def reduce_grid(
        self,
        longitudes,
        latitudes,
        elevations,
    ):
        cell_count = elevations.size

        if cell_count <= self.max_cells:
            return (
                longitudes,
                latitudes,
                elevations,
            )

        stride = int(
            math.ceil(
                math.sqrt(
                    cell_count
                    / self.max_cells
                )
            )
        )

        print(
            "Réduction grille Copernicus : "
            f"1 point sur {stride}"
        )

        return (
            longitudes[::stride, ::stride],
            latitudes[::stride, ::stride],
            elevations[::stride, ::stride],
        )

    def build(self):
        extent = (
            TerrainExtent
            .from_points(self.points)
            .add_margin(self.margin)
        )

        projection = self.projection

        tile_files = [
            self.download_tile(
                latitude,
                longitude,
            )
            for latitude, longitude
            in self.required_tiles(extent)
        ]

        datasets = [
            rasterio.open(tile_file)
            for tile_file in tile_files
        ]

        try:
            mosaic, transform = merge(
                datasets,
                bounds=(
                    extent.west,
                    extent.south,
                    extent.east,
                    extent.north,
                ),
                nodata=np.nan,
                dtype="float32",
                resampling=Resampling.bilinear,
            )
        finally:
            for dataset in datasets:
                dataset.close()

        elevations = self.fill_invalid_values(
            mosaic[0]
        )

        rows, columns = elevations.shape

        column_indices = (
            np.arange(columns)
            + 0.5
        )

        row_indices = (
            np.arange(rows)
            + 0.5
        )

        longitudes_1d = (
            transform.c
            + column_indices
            * transform.a
        )

        latitudes_1d = (
            transform.f
            + row_indices
            * transform.e
        )

        longitudes, latitudes = np.meshgrid(
            longitudes_1d,
            latitudes_1d,
        )

        (
            longitudes,
            latitudes,
            elevations,
        ) = self.reduce_grid(
            longitudes,
            latitudes,
            elevations,
        )

        print(
            "Projection DEM :",
            elevations.size,
            "points",
        )

        x, y = projection.project_arrays(
            latitudes,
            longitudes,
        )

        self.origin_x = float(
            x.min()
        )

        self.origin_y = float(
            y.min()
        )

        x -= self.origin_x
        y -= self.origin_y

        print(
            "Grille Copernicus :",
            elevations.shape[1],
            "x",
            elevations.shape[0],
        )

        print(
            "Altitude :",
            f"{elevations.min():.0f}",
            "à",
            f"{elevations.max():.0f}",
            "m",
        )

        return TerrainGrid(
            x,
            y,
            elevations,
        )
