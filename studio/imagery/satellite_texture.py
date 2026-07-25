from __future__ import annotations

import json
from pathlib import Path

import pyvista as pv


class SatelliteTexture:
    def __init__(self, gpx_file, cache_dir="cache/satellite", zoom=14, flip_vertical=True):
        self.gpx_file = Path(gpx_file)
        self.cache_dir = Path(cache_dir)
        self.zoom = int(zoom)
        self.flip_vertical = bool(flip_vertical)

        stem = self.gpx_file.stem
        self.image_file = self.cache_dir / f"{stem}_satellite_z{self.zoom}.png"
        self.metadata_file = self.cache_dir / f"{stem}_satellite_z{self.zoom}.json"

    def exists(self):
        return self.image_file.exists() and self.metadata_file.exists()

    def load_metadata(self):
        if not self.metadata_file.exists():
            raise FileNotFoundError(
                f"Métadonnées satellite introuvables : {self.metadata_file}"
            )
        return json.loads(self.metadata_file.read_text(encoding="utf-8"))

    def load_texture(self):
        if not self.image_file.exists():
            raise FileNotFoundError(
                f"Image satellite introuvable : {self.image_file}"
            )

        texture = pv.read_texture(str(self.image_file))

        if self.flip_vertical:
            texture.flip_y()

        return texture

    def describe(self):
        metadata = self.load_metadata()
        bounds = metadata.get("geographic_bounds_wgs84", {})

        return {
            "image": str(self.image_file),
            "metadata": str(self.metadata_file),
            "zoom": metadata.get("zoom", self.zoom),
            "west": bounds.get("west"),
            "south": bounds.get("south"),
            "east": bounds.get("east"),
            "north": bounds.get("north"),
        }
