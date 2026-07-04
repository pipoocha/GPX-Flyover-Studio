from studio.gpx_loader import GPXLoader
from studio.terrain.dem_loader import DEMLoader

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

dem = DEMLoader(points, "cache/dem")
dem.summary()