from studio.io.gpx_loader import GPXLoader
from studio.terrain.terrain_extent import TerrainExtent

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

extent = TerrainExtent.from_points(points)

print("Sans marge :")
print(extent)

print()

print("Avec marge :")
print(extent.add_margin(0.02))