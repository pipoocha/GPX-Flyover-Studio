from __future__ import annotations

import numpy as np
from pyproj import CRS, Transformer


class Projection:
    """Projection WGS84 ↔ UTM partagée par le DEM, la trace et la texture."""

    def __init__(self, points=None, epsg=None):
        if epsg is None:
            if not points:
                raise ValueError(
                    "Projection nécessite des points GPX ou un code EPSG."
                )

            lon = float(points[0]["lon"])
            lat = float(points[0]["lat"])

            zone = int((lon + 180.0) / 6.0) + 1
            epsg = 32600 + zone if lat >= 0.0 else 32700 + zone

        self.epsg = int(epsg)
        self.crs_wgs84 = CRS.from_epsg(4326)
        self.crs_projected = CRS.from_epsg(self.epsg)

        self.forward = Transformer.from_crs(
            self.crs_wgs84,
            self.crs_projected,
            always_xy=True,
        )

        self.inverse = Transformer.from_crs(
            self.crs_projected,
            self.crs_wgs84,
            always_xy=True,
        )

    def project_point(self, lat, lon):
        return self.forward.transform(float(lon), float(lat))

    def unproject_point(self, x, y):
        lon, lat = self.inverse.transform(float(x), float(y))
        return float(lat), float(lon)

    def project_arrays(self, latitudes, longitudes):
        x, y = self.forward.transform(
            np.asarray(longitudes, dtype=float),
            np.asarray(latitudes, dtype=float),
        )
        return np.asarray(x, dtype=float), np.asarray(y, dtype=float)

    def unproject_arrays(self, x, y):
        lon, lat = self.inverse.transform(
            np.asarray(x, dtype=float),
            np.asarray(y, dtype=float),
        )
        return np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)

    def project(self, points):
        latitudes = [float(point["lat"]) for point in points]
        longitudes = [float(point["lon"]) for point in points]
        x, y = self.project_arrays(latitudes, longitudes)
        return x.tolist(), y.tolist()
