from pathlib import Path

import contextily as ctx
import matplotlib.pyplot as plt
from pyproj import Transformer


class MapEngine:
    def __init__(self, points, config, cache_dir):
        self.points = points
        self.config = config
        self.cache_dir = Path(cache_dir)

    def get_provider(self):
        provider = self.config.get("map", "provider", default="OpenStreetMap")

        if provider == "OpenStreetMap":
            return ctx.providers.OpenStreetMap.Mapnik

        if provider == "EsriWorldImagery":
            return ctx.providers.Esri.WorldImagery

        if provider == "OpenTopoMap":
            return ctx.providers.OpenTopoMap

        if provider == "CartoDB.DarkMatter":
            return ctx.providers.CartoDB.DarkMatter

        return ctx.providers.OpenStreetMap.Mapnik

    def transform_points(self):
        lats = [p["lat"] for p in self.points]
        lons = [p["lon"] for p in self.points]

        transformer = Transformer.from_crs(
            "EPSG:4326",
            "EPSG:3857",
            always_xy=True
        )

        xs, ys = transformer.transform(lons, lats)

        return list(xs), list(ys)

    def bounds(self, padding=0.20):
        xs, ys = self.transform_points()

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        size = max(max_x - min_x, max_y - min_y)

        return (
            min_x - size * padding,
            max_x + size * padding,
            min_y - size * padding,
            max_y + size * padding,
        )

    def render_background(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        output_file = self.cache_dir / "background_map.png"

        min_x, max_x, min_y, max_y = self.bounds()

        fig, ax = plt.subplots(figsize=(16, 9))

        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)

        ctx.add_basemap(
            ax,
            source=self.get_provider(),
            zoom="auto"
        )

        ax.axis("off")
        plt.tight_layout()
        plt.savefig(output_file, dpi=120)
        plt.close(fig)

        print("Carte créée :", output_file)

        return output_file