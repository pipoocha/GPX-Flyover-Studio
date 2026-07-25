from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def read_gpx(gpx_file: Path):
    root = ET.parse(gpx_file).getroot()

    latitudes = []
    longitudes = []
    elevations = []

    for element in root.iter():
        if not element.tag.endswith("trkpt"):
            continue

        latitude = float(element.attrib["lat"])
        longitude = float(element.attrib["lon"])

        elevation = None

        for child in element:
            if child.tag.endswith("ele") and child.text:
                elevation = float(child.text)
                break

        if elevation is None:
            elevation = elevations[-1] if elevations else 0.0

        latitudes.append(latitude)
        longitudes.append(longitude)
        elevations.append(elevation)

    if len(elevations) < 2:
        raise ValueError("Le GPX ne contient pas assez de points.")

    return (
        np.asarray(latitudes, dtype=float),
        np.asarray(longitudes, dtype=float),
        np.asarray(elevations, dtype=float),
    )


def haversine_distances(latitudes, longitudes):
    earth_radius = 6_371_000.0

    lat_1 = np.radians(latitudes[:-1])
    lat_2 = np.radians(latitudes[1:])

    delta_latitude = lat_2 - lat_1
    delta_longitude = np.radians(
        longitudes[1:] - longitudes[:-1]
    )

    a = (
        np.sin(delta_latitude / 2.0) ** 2
        + np.cos(lat_1)
        * np.cos(lat_2)
        * np.sin(delta_longitude / 2.0) ** 2
    )

    segment_distances = (
        2.0
        * earth_radius
        * np.arctan2(
            np.sqrt(a),
            np.sqrt(1.0 - a),
        )
    )

    return np.insert(
        np.cumsum(segment_distances),
        0,
        0.0,
    )


def calculate_stats(distances, elevations):
    differences = np.diff(elevations)

    positive = differences[
        differences > 0
    ].sum()

    negative = -differences[
        differences < 0
    ].sum()

    return {
        "distance_km": float(distances[-1] / 1000.0),
        "gain": float(positive),
        "loss": float(negative),
        "minimum": float(elevations.min()),
        "maximum": float(elevations.max()),
    }


def render_outro_frames(
    distances,
    elevations,
    output_dir,
    width,
    height,
    fps,
    duration,
    title,
):
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stats = calculate_stats(
        distances,
        elevations,
    )

    total_frames = max(
        2,
        int(round(fps * duration)),
    )

    distances_km = distances / 1000.0

    y_margin = max(
        50.0,
        (elevations.max() - elevations.min()) * 0.12,
    )

    for frame_index in range(total_frames):
        progress = frame_index / max(
            1,
            total_frames - 1,
        )

        visible_index = max(
            2,
            int(
                round(
                    progress
                    * (len(elevations) - 1)
                )
            )
            + 1,
        )

        figure = plt.figure(
            figsize=(
                width / 100.0,
                height / 100.0,
            ),
            dpi=100,
            facecolor="#101010",
        )

        axis = figure.add_axes(
            [0.09, 0.20, 0.86, 0.64]
        )

        axis.set_facecolor("#101010")

        axis.plot(
            distances_km[:visible_index],
            elevations[:visible_index],
            linewidth=3.0,
            color="#FC4C02",
        )

        axis.fill_between(
            distances_km[:visible_index],
            elevations[:visible_index],
            elevations.min() - y_margin,
            alpha=0.18,
            color="#FC4C02",
        )

        marker_x = distances_km[visible_index - 1]
        marker_y = elevations[visible_index - 1]

        axis.scatter(
            [marker_x],
            [marker_y],
            s=70,
            color="#FC4C02",
            zorder=5,
        )

        axis.set_xlim(
            0.0,
            max(0.1, distances_km[-1]),
        )

        axis.set_ylim(
            elevations.min() - y_margin,
            elevations.max() + y_margin,
        )

        axis.set_xlabel(
            "Distance (km)",
            color="white",
            fontsize=12,
        )

        axis.set_ylabel(
            "Altitude (m)",
            color="white",
            fontsize=12,
        )

        axis.tick_params(
            colors="white",
            labelsize=10,
        )

        for spine in axis.spines.values():
            spine.set_color("#777777")

        axis.grid(
            alpha=0.18,
            linewidth=0.7,
        )

        figure.text(
            0.09,
            0.91,
            title,
            color="white",
            fontsize=20,
            weight="bold",
        )

        figure.text(
            0.09,
            0.08,
            (
                f"Distance {stats['distance_km']:.1f} km    "
                f"D+ {stats['gain']:.0f} m    "
                f"D− {stats['loss']:.0f} m    "
                f"Min {stats['minimum']:.0f} m    "
                f"Max {stats['maximum']:.0f} m"
            ),
            color="white",
            fontsize=13,
        )

        frame_file = (
            output_dir
            / f"outro_{frame_index:05d}.png"
        )

        figure.savefig(
            frame_file,
            facecolor=figure.get_facecolor(),
        )

        plt.close(figure)

        if (
            frame_index % 20 == 0
            or frame_index == total_frames - 1
        ):
            print(
                f"\rProfil {frame_index + 1}/{total_frames}",
                end="",
                flush=True,
            )

    print()


def run(command):
    print(
        " ".join(
            str(part)
            for part in command
        )
    )

    subprocess.run(
        command,
        check=True,
    )


def create_profile_video(
    frames_dir,
    fps,
    width,
    height,
    output_file,
):
    run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "outro_%05d.png"),
            "-vf",
            f"scale={width}:{height}:flags=lanczos,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            str(output_file),
        ]
    )


def concatenate_videos(
    main_video,
    outro_video,
    output_file,
    width,
    height,
    fps,
):
    filter_complex = (
        f"[0:v]scale={width}:{height},fps={fps},"
        "setsar=1[v0];"
        f"[1:v]scale={width}:{height},fps={fps},"
        "setsar=1[v1];"
        "[v0][v1]concat=n=2:v=1:a=0[outv]"
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(main_video),
            "-i",
            str(outro_video),
            "-filter_complex",
            filter_complex,
            "-map",
            "[outv]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(output_file),
        ]
    )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Ajoute un profil altimétrique animé "
            "à la fin d'une vidéo GPX."
        )
    )

    parser.add_argument(
        "video",
        type=Path,
    )

    parser.add_argument(
        "gpx",
        type=Path,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "output/video/final_with_profile.mp4"
        ),
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=6.0,
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--width",
        type=int,
        default=1280,
    )

    parser.add_argument(
        "--height",
        type=int,
        default=720,
    )

    parser.add_argument(
        "--title",
        default="Profil altimétrique",
    )

    return parser.parse_args()


def main():
    arguments = parse_arguments()

    if not arguments.video.exists():
        raise FileNotFoundError(
            f"Vidéo introuvable : {arguments.video}"
        )

    if not arguments.gpx.exists():
        raise FileNotFoundError(
            f"GPX introuvable : {arguments.gpx}"
        )

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg est introuvable dans le PATH."
        )

    (
        latitudes,
        longitudes,
        elevations,
    ) = read_gpx(
        arguments.gpx
    )

    distances = haversine_distances(
        latitudes,
        longitudes,
    )

    arguments.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix="gpx_profile_"
    ) as temporary_directory:
        temporary_path = Path(
            temporary_directory
        )

        frames_dir = (
            temporary_path / "frames"
        )

        outro_video = (
            temporary_path
            / "profile_outro.mp4"
        )

        render_outro_frames(
            distances=distances,
            elevations=elevations,
            output_dir=frames_dir,
            width=arguments.width,
            height=arguments.height,
            fps=arguments.fps,
            duration=arguments.duration,
            title=arguments.title,
        )

        create_profile_video(
            frames_dir=frames_dir,
            fps=arguments.fps,
            width=arguments.width,
            height=arguments.height,
            output_file=outro_video,
        )

        concatenate_videos(
            main_video=arguments.video,
            outro_video=outro_video,
            output_file=arguments.output,
            width=arguments.width,
            height=arguments.height,
            fps=arguments.fps,
        )

    print(
        "Vidéo finale :",
        arguments.output,
    )


if __name__ == "__main__":
    main()
