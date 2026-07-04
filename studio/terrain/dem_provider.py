from abc import ABC, abstractmethod
from pathlib import Path


class DEMProvider(ABC):

    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def download(self, extent, output_dir: Path):
        """
        Télécharge les données DEM couvrant 'extent'
        et retourne la liste des GeoTIFF téléchargés.
        """
        pass