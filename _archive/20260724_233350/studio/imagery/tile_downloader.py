from pathlib import Path
import requests
import mercantile

from studio.terrain.terrain_extent import TerrainExtent


class TileDownloader:
    def __init__(
        self,
        points,
        provider="esri",
        zoom=15,
        cache_dir="cache/tiles",
    ):
        self.points = points
        self.provider = provider
        self.zoom = zoom
        self.cache_dir = Path(cache_dir)

    def tile_url(self, tile):
        if self.provider == "esri":
            return (
                "https://server.arcgisonline.com/ArcGIS/rest/services/"
                f"World_Imagery/MapServer/tile/{tile.z}/{tile.y}/{tile.x}"
            )

        raise ValueError(f"Provider inconnu : {self.provider}")

    def tile_path(self, tile):
        return (
            self.cache_dir
            / self.provider
            / str(tile.z)
            / str(tile.x)
            / f"{tile.y}.jpg"
        )

    def tiles(self):
        extent = TerrainExtent.from_points(self.points).add_margin(0.02)

        return list(
            mercantile.tiles(
                extent.west,
                extent.south,
                extent.east,
                extent.north,
                self.zoom,
            )
        )

    def download(self):
        tiles = self.tiles()

        print(f"Tuiles à vérifier : {len(tiles)}")

        downloaded = 0
        cached = 0

        for i, tile in enumerate(tiles, start=1):
            path = self.tile_path(tile)

            if path.exists():
                cached += 1
                continue

            path.parent.mkdir(parents=True, exist_ok=True)

            url = self.tile_url(tile)

            response = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "GPX-Flyover-Studio"},
            )

            response.raise_for_status()

            path.write_bytes(response.content)
            downloaded += 1

            print(f"{i}/{len(tiles)} téléchargée : {path.name}")

        print()
        print(f"Déjà en cache : {cached}")
        print(f"Téléchargées : {downloaded}")

        return tiles