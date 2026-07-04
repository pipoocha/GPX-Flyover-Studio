from studio.io.gpx_loader import GPXLoader
from studio.render.renderer3d import Renderer3D

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

Renderer3D(points).show()