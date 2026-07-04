from pathlib import Path

import contextily as ctx
import matplotlib.pyplot as plt

from studio.terrain.terrain_extent import TerrainExtent


class SatelliteProvider:
    def __init__(self, points, output_file="cache/tiles/satellite.png", zoom=15):
        self.points = points
        self.output_file = Path(output_file)
        self.zoom = zoom
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def download(self):
        extent = TerrainExtent.from_points(self.points).add_margin(0.02)

        west = extent.west
        south = extent.south
        east = extent.east
        north = extent.north

        print("Téléchargement satellite...")

        img, ext = ctx.bounds2img(
            west,
            south,
            east,
            north,
            zoom=self.zoom,
            source=ctx.providers.Esri.WorldImagery,
            ll=True,
        )

        plt.imsave(self.output_file, img)

        print("Image satellite créée :", self.output_file)

        return self.output_file