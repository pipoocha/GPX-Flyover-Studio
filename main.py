from config.paths import DEFAULT_GPX, create_directories
from studio.app import FlyoverApp


if __name__ == "__main__":
    create_directories()

    app = FlyoverApp(
        gpx_file=str(DEFAULT_GPX)
    )

    app.run()