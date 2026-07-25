from math import radians, sin, cos, sqrt, atan2


class GPXStatistics:
    def __init__(self, points, config=None):
        self.points = points
        self.config = config

    def cfg(self, *keys, default=None):
        if self.config is None:
            return default
        return self.config.get(*keys, default=default)

    def haversine(self, p1, p2):
        r = 6371000

        lat1 = radians(p1["lat"])
        lon1 = radians(p1["lon"])
        lat2 = radians(p2["lat"])
        lon2 = radians(p2["lon"])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return r * c

    def total_distance_m(self):
        return sum(
            self.haversine(self.points[i - 1], self.points[i])
            for i in range(1, len(self.points))
        )
    def duration_seconds(self):
        manual_minutes = self.cfg("statistics", "manual_duration_minutes", default=0)

        if manual_minutes and manual_minutes > 0:
            return int(manual_minutes * 60)

        start = self.points[0].get("time")
        end = self.points[-1].get("time")

        if start is None or end is None:
            return None

        return int((end - start).total_seconds())
  

    def moving_duration_seconds(self):
        min_speed = self.cfg("statistics", "min_moving_speed_kmh", default=3)
        total = 0

        for i in range(1, len(self.points)):
            t1 = self.points[i - 1].get("time")
            t2 = self.points[i].get("time")

            if t1 is None or t2 is None:
                continue

            seconds = (t2 - t1).total_seconds()

            if seconds <= 0:
                continue

            dist_m = self.haversine(self.points[i - 1], self.points[i])
            speed_kmh = (dist_m / 1000) / (seconds / 3600)

            if speed_kmh >= min_speed:
                total += seconds

        return int(total)

    def elevation_gain_m(self):
        threshold = self.cfg("statistics", "elevation_threshold", default=3)
        gain = 0

        for i in range(1, len(self.points)):
            diff = self.points[i]["ele"] - self.points[i - 1]["ele"]
            if diff > threshold:
                gain += diff

        return gain

    def elevation_loss_m(self):
        threshold = self.cfg("statistics", "elevation_threshold", default=3)
        loss = 0

        for i in range(1, len(self.points)):
            diff = self.points[i]["ele"] - self.points[i - 1]["ele"]
            if diff < -threshold:
                loss += abs(diff)

        return loss

    def min_altitude_m(self):
        return min(p["ele"] for p in self.points)

    def max_altitude_m(self):
        return max(p["ele"] for p in self.points)

    def average_speed_kmh(self):
        duration = self.duration_seconds()

        if not duration or duration <= 0:
            return None

        return (self.total_distance_m() / 1000) / (duration / 3600)

    def moving_speed_kmh(self):
        moving = self.moving_duration_seconds()

        if not moving or moving <= 0:
            return None

        return (self.total_distance_m() / 1000) / (moving / 3600)

    def instant_speeds_kmh(self):
        speeds = []
        max_allowed = self.cfg("statistics", "max_speed_kmh", default=70)

        for i in range(1, len(self.points)):
            t1 = self.points[i - 1].get("time")
            t2 = self.points[i].get("time")

            if t1 is None or t2 is None:
                continue

            seconds = (t2 - t1).total_seconds()

            if seconds <= 0:
                continue

            dist_m = self.haversine(self.points[i - 1], self.points[i])
            speed = (dist_m / 1000) / (seconds / 3600)

            if speed <= max_allowed:
                speeds.append(speed)

        return speeds

    def max_speed_kmh(self):
        speeds = self.instant_speeds_kmh()

        if not speeds:
            return None

        return max(speeds)

    def bbox(self):
        lats = [p["lat"] for p in self.points]
        lons = [p["lon"] for p in self.points]

        return {
            "north": max(lats),
            "south": min(lats),
            "east": max(lons),
            "west": min(lons),
        }

    def format_time(self, seconds):
        if seconds is None:
            return "non disponible"

        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60

        return f"{h:02d}:{m:02d}:{s:02d}"

    def summary(self):
        duration = self.duration_seconds()
        moving = self.moving_duration_seconds()
        avg = self.average_speed_kmh()
        moving_avg = self.moving_speed_kmh()
        vmax = self.max_speed_kmh()

        print("===== STATISTIQUES =====")
        print(f"Distance : {self.total_distance_m() / 1000:.2f} km")
        print(f"D+ filtré : {self.elevation_gain_m():.0f} m")
        print(f"D- filtré : {self.elevation_loss_m():.0f} m")
        print(f"Altitude min : {self.min_altitude_m():.0f} m")
        print(f"Altitude max : {self.max_altitude_m():.0f} m")
        print(f"Durée totale : {self.format_time(duration)}")
        print(f"Temps en mouvement : {self.format_time(moving)}")

        if avg:
            print(f"Vitesse moyenne totale : {avg:.1f} km/h")

        if moving_avg:
            print(f"Vitesse moyenne en mouvement : {moving_avg:.1f} km/h")

        if vmax:
            print(f"Vitesse max filtrée : {vmax:.1f} km/h")

        print("BBox :", self.bbox())

    def to_dict(self):
        return {
            "distance_km": round(self.total_distance_m() / 1000, 2),
            "elevation_gain_m": round(self.elevation_gain_m(), 0),
            "elevation_loss_m": round(self.elevation_loss_m(), 0),
            "altitude_min_m": round(self.min_altitude_m(), 0),
            "altitude_max_m": round(self.max_altitude_m(), 0),
            "duration_seconds": self.duration_seconds(),
            "moving_duration_seconds": self.moving_duration_seconds(),
            "average_speed_kmh": (
                round(self.average_speed_kmh(), 1)
                if self.average_speed_kmh()
                else None
            ),
            "moving_speed_kmh": (
                round(self.moving_speed_kmh(), 1)
                if self.moving_speed_kmh()
                else None
            ),
            "max_speed_kmh": (
                round(self.max_speed_kmh(), 1)
                if self.max_speed_kmh()
                else None
            ),
            "bbox": self.bbox(),
        }