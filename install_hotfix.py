from __future__ import annotations

from datetime import datetime
from pathlib import Path
import py_compile
import shutil

ROOT = Path(__file__).resolve().parent
PIPELINE = ROOT / "studio/core/pipeline.py"
GUI = ROOT / "studio/gui/main_window.py"


def backup(paths):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = ROOT / "_archive" / f"before_hotfix_{stamp}"
    for path in paths:
        target = folder / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return folder


def patch_pipeline(text):
    if "self.terrain_projection = None" not in text:
        marker = "        self.satellite_texture = None\n"
        if marker not in text:
            raise RuntimeError("Initialisation pipeline introuvable.")
        text = text.replace(
            marker,
            marker + "        self.terrain_projection = None\n",
            1,
        )

    old = """        self.project.grid = builder.build()
        self.project.mesh = TerrainMesh(self.project.grid).build()
        self.project.sampler = TerrainSampler(self.project.grid)

        self.origin_x = float(builder.origin_x)
        self.origin_y = float(builder.origin_y)
"""
    new = """        self.project.grid = builder.build()
        self.terrain_projection = builder.projection
        self.project.mesh = TerrainMesh(self.project.grid).build()
        self.project.sampler = TerrainSampler(self.project.grid)

        self.origin_x = float(builder.origin_x)
        self.origin_y = float(builder.origin_y)
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "self.terrain_projection = builder.projection" not in text:
        raise RuntimeError("Bloc build_terrain introuvable.")

    old_call = """        self.project.path_coords = PathBuilder(
            self.project.points,
            origin_x=self.origin_x,
            origin_y=self.origin_y,
            sampler=self.project.sampler,
            z_offset=self.project.track.z_offset,
        ).build()
"""
    new_call = """        self.project.path_coords = PathBuilder(
            self.project.points,
            origin_x=self.origin_x,
            origin_y=self.origin_y,
            sampler=self.project.sampler,
            projection=self.terrain_projection,
            z_offset=self.project.track.z_offset,
        ).build()
"""
    if old_call in text:
        text = text.replace(old_call, new_call, 1)
    elif "projection=self.terrain_projection" not in text:
        raise RuntimeError("Appel PathBuilder introuvable.")

    return text


def patch_gui(text):
    old = """        def refresh_value(*_):
            value = variable.get()
"""
    new = """        def refresh_value(*_):
            try:
                value = variable.get()
            except (tk.TclError, ValueError):
                value_label.configure(text="")
                return
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "except (tk.TclError, ValueError):" not in text:
        raise RuntimeError("refresh_value introuvable.")
    return text


def main():
    for path in (PIPELINE, GUI):
        if not path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {path}")

    saved = backup([PIPELINE, GUI])

    try:
        PIPELINE.write_text(
            patch_pipeline(PIPELINE.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
        GUI.write_text(
            patch_gui(GUI.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
        py_compile.compile(str(PIPELINE), doraise=True)
        py_compile.compile(str(GUI), doraise=True)
    except Exception:
        shutil.copy2(saved / PIPELINE.relative_to(ROOT), PIPELINE)
        shutil.copy2(saved / GUI.relative_to(ROOT), GUI)
        raise

    print("Correctif installé.")
    print("Sauvegarde :", saved)


if __name__ == "__main__":
    main()
