from __future__ import annotations

import json
from pathlib import Path

import pyvista as pv

import config


class SatelliteTexture:
    def __init__(self, gpx_file, cache_dir="cache/satellite", zoom=14, flip_vertical=True):
        self.gpx_file = Path(gpx_file)
        self.cache_dir = Path(cache_dir)
        self.zoom = int(zoom)
        self.flip_vertical = bool(flip_vertical)

        stem = self.gpx_file.stem
        self.image_file = self.cache_dir / f"{stem}_satellite_z{self.zoom}.png"
        self.preview_image_file = (
            self.cache_dir / f"{stem}_satellite_z{self.zoom}_preview.png"
        )
        self.video_image_file = (
            self.cache_dir / f"{stem}_satellite_z{self.zoom}_video.png"
        )
        self.metadata_file = self.cache_dir / f"{stem}_satellite_z{self.zoom}.json"

    def preferred_image_file(self):
        mode = str(getattr(config, "MODE", "PREVIEW")).upper()
        if mode == "PREVIEW" and self.preview_image_file.exists():
            return self.preview_image_file
        if mode == "VIDEO" and self.video_image_file.exists():
            return self.video_image_file
        if self.video_image_file.exists():
            return self.video_image_file
        if self.preview_image_file.exists():
            return self.preview_image_file
        return self.image_file

    def exists(self):
        return self.image_file.exists() and self.metadata_file.exists()

    def load_metadata(self):
        if not self.metadata_file.exists():
            raise FileNotFoundError(
                f"Métadonnées satellite introuvables : {self.metadata_file}"
            )
        return json.loads(self.metadata_file.read_text(encoding="utf-8"))

    def load_texture(self):
        selected_image = self.preferred_image_file()

        if not selected_image.exists():
            raise FileNotFoundError(
                f"Image satellite introuvable : {selected_image}"
            )

        print("Texture satellite chargée :", selected_image)
        texture = pv.read_texture(str(selected_image))

        if self.flip_vertical:
            texture.flip_y()

        return texture

    def describe(self):
        metadata = self.load_metadata()
        bounds = metadata.get("geographic_bounds_wgs84", {})

        selected_image = self.preferred_image_file()

        return {
            "image": str(selected_image),
            "source_image": str(self.image_file),
            "preview_image": str(self.preview_image_file),
            "video_image": str(self.video_image_file),
            "metadata": str(self.metadata_file),
            "zoom": metadata.get("zoom", self.zoom),
            "west": bounds.get("west"),
            "south": bounds.get("south"),
            "east": bounds.get("east"),
            "north": bounds.get("north"),
        }
