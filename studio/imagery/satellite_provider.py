from pathlib import Path

import contextily as ctx
import matplotlib.pyplot as plt

from studio.terrain.terrain_extent import TerrainExtent


class SatelliteProvider:
    def __init__(self, points, output_file, zoom=15):
        self.points = points
        self.output_file = Path(output_file)
        self.zoom = zoom
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def get_texture(self):
        if self.output_file.exists():
            print("Texture satellite trouvée :", self.output_file)
            return self.output_file

        extent = TerrainExtent.from_points(self.points).add_margin(0.02)

        print("Téléchargement texture satellite...")

        img, _ = ctx.bounds2img(
            extent.west,
            extent.south,
            extent.east,
            extent.north,
            zoom=self.zoom,
            source=ctx.providers.Esri.WorldImagery,
            ll=True,
        )

        plt.imsave(self.output_file, img)

        print("Texture satellite créée :", self.output_file)

        return self.output_file