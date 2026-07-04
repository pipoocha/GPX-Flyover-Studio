from studio.io.gpx_loader import GPXLoader
from studio.imagery.tile_downloader import TileDownloader

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

downloader = TileDownloader(
    points,
    provider="esri",
    zoom=15,
)

downloader.download()