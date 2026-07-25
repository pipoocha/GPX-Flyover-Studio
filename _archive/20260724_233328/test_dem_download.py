from studio.io.gpx_loader import GPXLoader
from studio.terrain.dem_downloader import DEMDownloader

loader = GPXLoader("gpx/28 km Ranchal.gpx")
points = loader.load()

downloader = DEMDownloader(points)
downloader.download()