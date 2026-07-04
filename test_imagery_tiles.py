import mercantile

from studio.io.gpx_loader import GPXLoader
from studio.terrain.terrain_extent import TerrainExtent

ZOOM = 15

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

extent = TerrainExtent.from_points(points).add_margin(0.02)

tiles = list(
    mercantile.tiles(
        extent.west,
        extent.south,
        extent.east,
        extent.north,
        ZOOM,
    )
)

print("Zoom :", ZOOM)
print("Nombre de tuiles :", len(tiles))

for tile in tiles[:20]:
    print(tile)

if len(tiles) > 20:
    print("...")