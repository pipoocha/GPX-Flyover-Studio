import sys

import config
from config.paths import DEFAULT_GPX, create_directories
from studio.core.app import FlyoverApp


def set_mode():
    if len(sys.argv) < 2:
        return

    mode = sys.argv[1].upper()

    if mode not in ("PREVIEW", "DEV", "PROD"):
        print("Mode inconnu :", mode)
        print("Utilisation :")
        print("   python main.py preview")
        print("   python main.py dev")
        print("   python main.py prod")
        sys.exit(1)

    config.MODE = mode


if __name__ == "__main__":
    create_directories()
    set_mode()

    print("===================================")
    print("GPX Flyover Studio")
    print("Mode :", config.MODE)
    print("===================================")

    app = FlyoverApp(
        gpx_file=str(DEFAULT_GPX)
    )

    app.run()