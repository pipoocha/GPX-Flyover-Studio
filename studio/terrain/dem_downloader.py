from pathlib import Path
import elevation

from studio.terrain.terrain_extent import TerrainExtent


class DEMDownloader:
    def __init__(self, points, output_file="cache/dem/ranchal_dem.tif"):
        self.points = points
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def download(self):
        extent = TerrainExtent.from_points(self.points).add_margin(0.02)

        bounds = (
            extent.west,
            extent.south,
            extent.east,
            extent.north,
        )

        print("Téléchargement DEM...")
        print("Bounds :", bounds)

        elevation.clip(
            bounds=bounds,
            output=str(self.output_file),
        )

        print("DEM créé :", self.output_file)

        return self.output_file