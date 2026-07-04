from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

GPX_DIR = ROOT_DIR / "gpx"
CACHE_DIR = ROOT_DIR / "cache"
FRAMES_DIR = CACHE_DIR / "frames"
TILES_DIR = CACHE_DIR / "tiles"

OUTPUT_DIR = ROOT_DIR / "output"
VIDEO_DIR = OUTPUT_DIR / "video"
LOG_DIR = OUTPUT_DIR / "logs"

DEFAULT_GPX = GPX_DIR / "28 km Ranchal.gpx"
DEFAULT_VIDEO = VIDEO_DIR / "flyover.mp4"


def create_directories():
    for folder in [
        GPX_DIR,
        CACHE_DIR,
        FRAMES_DIR,
        TILES_DIR,
        OUTPUT_DIR,
        VIDEO_DIR,
        LOG_DIR,
    ]:
        folder.mkdir(parents=True, exist_ok=True)