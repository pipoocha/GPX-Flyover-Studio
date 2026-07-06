import sys
from pathlib import Path

import config
from config.paths import DEFAULT_GPX, create_directories
from studio.core.app import FlyoverApp
from studio.core.project_loader import ProjectLoader


def parse_size(value):
    width, height = value.lower().split("x")
    return int(width), int(height)


def apply_option(option, value):
    if option == "--duration":
        config.VIDEO_DURATION = int(value)
        config.TOTAL_FRAMES = config.VIDEO_DURATION * config.FPS

    elif option == "--fps":
        config.FPS = int(value)
        config.TOTAL_FRAMES = config.VIDEO_DURATION * config.FPS

    elif option == "--output":
        config.DEFAULT_VIDEO = Path(value)

    elif option == "--size":
        width, height = parse_size(value)
        config.WINDOW_WIDTH = width
        config.WINDOW_HEIGHT = height

    else:
        print("Option inconnue :", option)
        sys.exit(1)


def parse_args():
    args = sys.argv[1:]

    if not args:
        return DEFAULT_GPX

    if args[0].lower() == "project":
        if len(args) < 2:
            print("Projet manquant.")
            print("Exemple : python main.py project projects\\ranchal.yaml")
            sys.exit(1)

        project_file = args[1]
        remaining = args[2:]

        gpx_file = ProjectLoader(project_file).load()

    else:
        gpx_file = DEFAULT_GPX

        first = args.pop(0)

        if first.upper() in ("PREVIEW", "DEV", "PROD"):
            config.MODE = first.upper()
        else:
            gpx_file = Path(first)

        if args and not args[0].startswith("--"):
            gpx_file = Path(args.pop(0))

        remaining = args

    while remaining:
        option = remaining.pop(0)

        if option == "--help":
            print("Utilisation :")
            print("  python main.py preview")
            print("  python main.py dev")
            print("  python main.py prod")
            print("  python main.py project projects\\ranchal.yaml")
            sys.exit(0)

        if not remaining:
            print("Valeur manquante pour", option)
            sys.exit(1)

        value = remaining.pop(0)
        apply_option(option, value)

    return gpx_file


if __name__ == "__main__":
    create_directories()

    gpx_file = parse_args()

    if not Path(gpx_file).exists():
        print("GPX introuvable :")
        print(gpx_file)
        sys.exit(1)

    print("===================================")
    print(config.PROJECT_TITLE)
    print("Mode :", config.MODE)
    print("GPX  :", gpx_file)
    print("Durée:", config.VIDEO_DURATION, "s")
    print("FPS  :", config.FPS)
    print("Frames:", config.TOTAL_FRAMES)
    print("Taille:", f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
    print("Sortie:", config.DEFAULT_VIDEO)
    print("===================================")

    app = FlyoverApp(
        gpx_file=str(gpx_file)
    )

    app.run()