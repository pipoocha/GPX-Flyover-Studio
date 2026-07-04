from pathlib import Path

from studio.terrain.dem_reader import DEMReader


class DEMLoader:

    def __init__(self, cache_folder="cache/dem"):
        self.cache = Path(cache_folder)

    def load(self):

        tif_files = sorted(self.cache.glob("*.tif"))

        if not tif_files:
            raise FileNotFoundError(
                "Aucun fichier DEM (.tif) trouvé dans cache/dem"
            )

        print(f"DEM trouvé : {tif_files[0].name}")

        return DEMReader(tif_files[0]).load()