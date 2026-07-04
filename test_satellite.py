from studio.io.gpx_loader import GPXLoader
from studio.terrain.satellite_provider import SatelliteProvider

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

provider = SatelliteProvider(points, zoom=15)
provider.download()