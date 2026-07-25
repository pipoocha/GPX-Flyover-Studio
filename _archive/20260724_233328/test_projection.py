from studio.io.gpx_loader import GPXLoader
from studio.terrain.projection import Projection

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

proj = Projection(points)

xs, ys = proj.project()

print("Premier point")
print(xs[0], ys[0])

print("Dernier point")
print(xs[-1], ys[-1])