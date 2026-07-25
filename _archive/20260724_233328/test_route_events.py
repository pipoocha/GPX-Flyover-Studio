from studio.animation.progress_path import (
    ProgressPath,
)
from studio.director.route_event_analyzer import (
    RouteEventAnalyzer,
)
from studio.geometry.path_builder import (
    PathBuilder,
)
from studio.io.gpx_loader import GPXLoader
from studio.terrain.srtm_grid import (
    SRTMGridBuilder,
)
from studio.terrain.terrain_sampler import (
    TerrainSampler,
)


GPX_FILE = "gpx/test_5km.gpx"


points = GPXLoader(
    GPX_FILE
).load()

builder = SRTMGridBuilder(
    points,
    resolution=0.0005,
)

grid = builder.build()

sampler = TerrainSampler(
    grid
)

path_coords = PathBuilder(
    points,
    origin_x=builder.origin_x,
    origin_y=builder.origin_y,
    sampler=sampler,
    z_offset=60,
).build()

progress_path = ProgressPath(
    path_coords
)

analyzer = RouteEventAnalyzer(
    path_coords,
    smoothing_window=41,
    prominence_threshold=20.0,
    minimum_spacing_m=300.0,
    steep_slope_threshold=0.08,
)

events = analyzer.analyze()

print()
print(
    "Distance totale :",
    f"{progress_path.total_distance / 1000:.2f} km",
)

print(
    "Nombre d'événements :",
    len(events),
)

for event in events:
    print(
        event.event_type,
        "|",
        f"{event.distance_km:.2f} km",
        "|",
        f"{event.altitude:.0f} m",
        "|",
        f"{event.progress * 100:.1f} %",
        "| pente",
        f"{event.slope * 100:.1f} %",
    )