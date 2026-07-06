import sys
from pathlib import Path

import config
from config.paths import DEFAULT_GPX, create_directories
from studio.core.app import FlyoverApp


def parse_args():
    mode = config.MODE
    gpx_file = DEFAULT_GPX
    output_file = config.DEFAULT_VIDEO

    args = sys.argv[1:]

    if args:
        first = args.pop(0)

        if first.upper() in ("PREVIEW", "DEV", "PROD"):
            mode = first.upper()
        else:
            gpx_file = Path(first)

    if args and not args[0].startswith("--"):
        gpx_file = Path(args.pop(0))

    while args:
        option = args.pop(0)

        if option == "--duration" and args:
            config.VIDEO_DURATION = int(args.pop(0))
            config.TOTAL_FRAMES = config.VIDEO_DURATION * config.FPS

        elif option == "--fps" and args:
            config.FPS = int(args.pop(0))
            config.TOTAL_FRAMES = config.VIDEO_DURATION * config.FPS

        elif option == "--output" and args:
            output_file = Path(args.pop(0))
            config.DEFAULT_VIDEO = output_file

        elif option == "--help":
            print("Utilisation :")
            print("  python main.py preview")
            print("  python main.py dev")
            print("  python main.py prod")
            print('  python main.py dev "gpx\\mon_parcours.gpx" --duration 45 --fps 25')
            print('  python main.py dev "gpx\\mon_parcours.gpx" --output "output\\video\\test.mp4"')
            sys.exit(0)

        else:
            print("Option inconnue :", option)
            sys.exit(1)

    config.MODE = mode

    return gpx_file, output_file


if __name__ == "__main__":
    create_directories()

    gpx_file, output_file = parse_args()

    if not Path(gpx_file).exists():
        print("GPX introuvable :")
        print(gpx_file)
        sys.exit(1)

    print("===================================")
    print("GPX Flyover Studio")
    print("Mode :", config.MODE)
    print("GPX  :", gpx_file)
    print("Durée:", config.VIDEO_DURATION, "s")
    print("FPS  :", config.FPS)
    print("Frames:", config.TOTAL_FRAMES)
    print("Sortie:", output_file)
    print("===================================")

    app = FlyoverApp(
        gpx_file=str(gpx_file)
    )

    app.run()