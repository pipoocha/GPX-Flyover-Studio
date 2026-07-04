from pathlib import Path
import gpxpy


class GPXLoader:
    def __init__(self, filename):
        self.filename = Path(filename)
        self.points = []

    def load(self):
        if not self.filename.exists():
            raise FileNotFoundError(f"GPX introuvable : {self.filename}")

        with open(self.filename, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)

        self.points = []

        for track in gpx.tracks:
            for segment in track.segments:
                for p in segment.points:
                    self.points.append({
                        "lat": p.latitude,
                        "lon": p.longitude,
                        "ele": p.elevation if p.elevation is not None else 0.0,
                        "time": p.time,
                    })

        if not self.points:
            raise ValueError("Aucun point trouvé dans le GPX.")

        return self.points

    def summary(self):
        print("===== GPX =====")
        print("Fichier :", self.filename)
        print("Points :", len(self.points))
        print("Départ :", self.points[0])
        print("Arrivée :", self.points[-1])