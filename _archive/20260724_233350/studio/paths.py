from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

CONFIG_FILE = PROJECT_DIR / "config.yaml"
GPX_DIR = PROJECT_DIR / "gpx"
CACHE_DIR = PROJECT_DIR / "cache"
OUTPUT_DIR = PROJECT_DIR / "output"
ASSETS_DIR = PROJECT_DIR / "assets"

for folder in [GPX_DIR, CACHE_DIR, OUTPUT_DIR, ASSETS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)