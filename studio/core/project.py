from dataclasses import dataclass


@dataclass
class FlyoverProject:
    gpx_file: str
    points: list | None = None
    grid: object | None = None
    mesh: object | None = None
    sampler: object | None = None
    path_coords: object | None = None