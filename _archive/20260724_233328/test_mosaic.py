from studio.io.gpx_loader import GPXLoader
from studio.imagery.tile_downloader import TileDownloader
from studio.imagery.mosaic_builder import MosaicBuilder

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

downloader = TileDownloader(
    points,
    provider="esri",
    zoom=15,
)

tiles = downloader.download()

mosaic = MosaicBuilder(
    tiles,
    provider="esri",
    zoom=15,
).build()

print(mosaic)