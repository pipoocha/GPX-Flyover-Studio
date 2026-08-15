from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from studio.config.loader import ProjectLoaderV5
from studio.core.pipeline import FlyoverPipeline
from studio.core.project import Project
from studio.rendering.render_engine import RenderEngine


BACKGROUNDS = (
    ("satellite_natural", "Satellite naturel"),
    ("satellite_original", "Satellite original"),
    ("relief_natural", "Relief naturel"),
    ("relief_topographic", "Relief topographique"),
)


def render_comparison(project_file: Path, progress: float = 0.45) -> Path:
    config = ProjectLoaderV5(project_file).load(require_existing_gpx=True)
    project = Project(config)

    # Le comparateur a besoin de l'imagerie satellite même si le fond courant
    # du projet est un relief coloré.
    project.terrain.satellite = True
    pipeline = FlyoverPipeline(project)
    pipeline.load_gpx()
    pipeline.build_terrain()
    pipeline.load_satellite_texture(force=True)
    pipeline.build_path()
    camera_path = pipeline.build_camera()

    output_dir = Path("output/comparisons")
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(project.gpx_file).stem
    images: list[tuple[str, Image.Image]] = []

    old_width, old_height = project.video.width, project.video.height
    project.video.width, project.video.height = 960, 540

    for background, label in BACKGROUNDS:
        scene = pipeline.build_scene(off_screen=True, background_override=background)
        renderer = RenderEngine(scene, camera_path, project.path_coords)
        renderer.create()
        renderer.update(progress, force_track=True)
        scene.plotter.render()
        file_path = output_dir / f"{stem}_{background}.png"
        scene.plotter.screenshot(str(file_path))
        scene.plotter.close()
        with Image.open(file_path) as image:
            images.append((label, image.convert("RGB").copy()))

    project.video.width, project.video.height = old_width, old_height

    tile_w, tile_h = 960, 540
    label_h = 46
    canvas = Image.new("RGB", (tile_w * 2, (tile_h + label_h) * 2), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    for index, (label, image) in enumerate(images):
        col = index % 2
        row = index // 2
        x = col * tile_w
        y = row * (tile_h + label_h)
        canvas.paste(image.resize((tile_w, tile_h)), (x, y))
        draw.rectangle((x, y + tile_h, x + tile_w, y + tile_h + label_h), fill=(245, 245, 245))
        draw.text((x + 14, y + tile_h + 14), label, fill=(25, 25, 25), font=font)

    output = output_dir / f"{stem}_comparaison_fonds.png"
    canvas.save(output, quality=95)
    return output.resolve()


def open_file(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}" >/dev/null 2>&1 &')
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Comparer les fonds Flyover Studio")
    parser.add_argument("project", type=Path)
    parser.add_argument("--progress", type=float, default=0.45)
    args = parser.parse_args()
    output = render_comparison(args.project, max(0.05, min(0.95, args.progress)))
    print(f"Comparaison créée : {output}")
    open_file(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
