from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config.paths import create_directories
from studio.config.loader import ProjectLoaderV5
from studio.core.app import FlyoverApp
from studio.core.project import Project


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="GPX Flyover Studio V5"
    )

    parser.add_argument(
        "command",
        choices=("project",),
    )

    parser.add_argument(
        "project_file",
        type=Path,
    )

    parser.add_argument(
        "--mode",
        choices=("PREVIEW", "VIDEO"),
    )

    return parser.parse_args()


def main():
    arguments = parse_arguments()
    create_directories()

    project_config = ProjectLoaderV5(
        arguments.project_file
    ).load(require_existing_gpx=True)

    if arguments.mode:
        project_config.video.mode = arguments.mode

    project = Project(project_config)

    print("===================================")
    print(project.title)
    print("Mode :", project.video.mode)
    print("GPX  :", project.gpx_file)
    print("Durée:", project.timeline.travel, "s")
    print("FPS  :", project.video.fps)
    print("Taille:", project.video.resolution)
    print("Sortie:", project.video.output)
    print("===================================")

    FlyoverApp(project).run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompu.")
        sys.exit(130)
    except Exception as error:
        print("\nERREUR :", error)
        raise
