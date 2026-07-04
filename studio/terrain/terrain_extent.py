from dataclasses import dataclass


@dataclass
class TerrainExtent:
    west: float
    east: float
    south: float
    north: float

    @property
    def width(self):
        return self.east - self.west

    @property
    def height(self):
        return self.north - self.south

    def add_margin(self, margin=0.01):
        return TerrainExtent(
            west=self.west - margin,
            east=self.east + margin,
            south=self.south - margin,
            north=self.north + margin,
        )

    @classmethod
    def from_points(cls, points):
        lats = [p["lat"] for p in points]
        lons = [p["lon"] for p in points]

        return cls(
            west=min(lons),
            east=max(lons),
            south=min(lats),
            north=max(lats),
        )