import sys
from pathlib import Path

import config
from config.paths import DEFAULT_GPX, create_directories
from studio.core.app import FlyoverApp


def parse_args():
    mode = config.MODE
    gpx_file = DEFAULT_GPX

    if len(sys.argv) >= 2:
        candidate = sys.argv[1].upper()

        if candidate in ("PREVIEW", "DEV", "PROD"):
            mode = candidate
        else:
            gpx_file = Path(sys.argv[1])

    if len(sys.argv) >= 3:
        gpx_file = Path(sys.argv[2])

    config.MODE = mode

    return gpx_file


if __name__ == "__main__":
    create_directories()

    gpx_file = parse_args()

    if not Path(gpx_file).exists():
        print("GPX introuvable :")
        print(gpx_file)
        sys.exit(1)

    print("===================================")
    print("GPX Flyover Studio")
    print("Mode :", config.MODE)
    print("GPX  :", gpx_file)
    print("===================================")

    app = FlyoverApp(
        gpx_file=str(gpx_file)
    )

    app.run()