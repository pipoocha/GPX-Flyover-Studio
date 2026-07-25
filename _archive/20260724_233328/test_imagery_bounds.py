from studio.io.gpx_loader import GPXLoader
from studio.terrain.terrain_extent import TerrainExtent

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

extent = TerrainExtent.from_points(points).add_margin(0.02)

print("WEST :", extent.west)
print("SOUTH:", extent.south)
print("EAST :", extent.east)
print("NORTH:", extent.north)