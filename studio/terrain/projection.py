from pyproj import CRS, Transformer


class Projection:
    def __init__(self, points):
        lon = points[0]["lon"]
        lat = points[0]["lat"]

        zone = int((lon + 180) / 6) + 1
        epsg = 32600 + zone if lat >= 0 else 32700 + zone

        self.transformer = Transformer.from_crs(
            CRS.from_epsg(4326),
            CRS.from_epsg(epsg),
            always_xy=True,
        )

    def project_point(self, lat, lon):
        return self.transformer.transform(lon, lat)

    def project(self, points):
        xs = []
        ys = []

        for p in points:
            x, y = self.project_point(p["lat"], p["lon"])
            xs.append(x)
            ys.append(y)

        return xs, ys