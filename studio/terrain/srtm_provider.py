import srtm


class SRTMProvider:
    def __init__(self):
        print("Chargement SRTM...")
        self.data = srtm.get_data()

    def elevation(self, lat, lon):
        h = self.data.get_elevation(lat, lon)
        return float(h) if h is not None else 0.0