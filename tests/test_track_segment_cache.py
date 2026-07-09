from studio.io.gpx_loader import GPXLoader
from studio.terrain.srtm_grid import SRTMGridBuilder
from studio.terrain.terrain_sampler import TerrainSampler
from studio.geometry.path_builder import PathBuilder
from studio.animation.track_segment_cache import TrackSegmentCache


loader = GPXLoader("gpx/20_km_belmont.gpx")
points = loader.load()

builder = SRTMGridBuilder(points, resolution=0.0005)
grid = builder.build()

sampler = TerrainSampler(grid)

path_coords = PathBuilder(
    points,
    origin_x=builder.origin_x,
    origin_y=builder.origin_y,
    sampler=sampler,
    z_offset=60,
).build()

cache = TrackSegmentCache(
    path_coords,
    segment_points=30,
    radius=7,
    sides=8,
    mode="line",
)

segments = cache.build()

print("OK")
print("Nombre de segments :", len(segments))