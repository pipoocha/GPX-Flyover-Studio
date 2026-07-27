from __future__ import annotations

import argparse
import importlib
import py_compile
import subprocess
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORE_FILES = (
    "main.py",
    "studio/core/app.py",
    "studio/core/pipeline.py",
    "studio/config/models.py",
    "studio/config/loader.py",
    "studio/gui/main_window.py",
    "studio/geometry/path_builder.py",
    "studio/terrain/terrain_mesh.py",
    "studio/terrain/terrain_sampler.py",
    "studio/imagery/satellite_texture.py",
    "studio/leader/leader.py",
    "studio/animation/preview_player.py",
    "studio/animation/frame_renderer.py",
)

IMPORTS = (
    "studio.core.app",
    "studio.core.pipeline",
    "studio.config.models",
    "studio.config.loader",
    "studio.gui.main_window",
    "studio.geometry.path_builder",
    "studio.terrain.terrain_mesh",
    "studio.terrain.terrain_sampler",
    "studio.imagery.satellite_texture",
    "studio.leader.leader",
    "studio.animation.preview_player",
    "studio.animation.frame_renderer",
)


class CheckResult:
    def __init__(self, title: str):
        self.title = title
        self.ok = True
        self.messages: list[str] = []

    def pass_(self, message: str):
        self.messages.append(f"  OK  {message}")

    def fail(self, message: str):
        self.ok = False
        self.messages.append(f"  KO  {message}")

    def warn(self, message: str):
        self.messages.append(f"  !   {message}")

    def print(self):
        status = "OK" if self.ok else "ÉCHEC"
        print(f"\n[{status}] {self.title}")
        for message in self.messages:
            print(message)


def compile_files() -> CheckResult:
    result = CheckResult("Compilation Python")

    for relative in CORE_FILES:
        file = PROJECT_ROOT / relative

        if not file.exists():
            result.fail(f"Fichier absent : {relative}")
            continue

        try:
            py_compile.compile(
                str(file),
                cfile=str(PROJECT_ROOT / "__pycache_stabilisation__.pyc"),
                doraise=True,
            )
            result.pass_(relative)
        except Exception as error:
            result.fail(f"{relative} : {error}")

    temp = PROJECT_ROOT / "__pycache_stabilisation__.pyc"
    temp.unlink(missing_ok=True)
    return result


def import_modules() -> CheckResult:
    result = CheckResult("Imports principaux")

    sys.path.insert(0, str(PROJECT_ROOT))

    for module_name in IMPORTS:
        try:
            importlib.import_module(module_name)
            result.pass_(module_name)
        except Exception as error:
            result.fail(f"{module_name} : {error}")

    return result


def locate_project(project_arg: str | None) -> Path | None:
    if project_arg:
        return Path(project_arg)

    candidates = sorted(
        (PROJECT_ROOT / "projects").glob("*.yaml"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    return candidates[0] if candidates else None


def check_yaml(project_file: Path | None) -> CheckResult:
    result = CheckResult("Projet YAML")

    if project_file is None:
        result.fail("Aucun YAML trouvé dans projects/.")
        return result

    if not project_file.is_absolute():
        project_file = PROJECT_ROOT / project_file

    if not project_file.exists():
        result.fail(f"Projet introuvable : {project_file}")
        return result

    try:
        data = yaml.safe_load(
            project_file.read_text(encoding="utf-8")
        ) or {}
    except Exception as error:
        result.fail(f"YAML illisible : {error}")
        return result

    required_sections = (
        "project",
        "gpx",
        "camera",
        "track",
        "leader",
        "terrain",
        "timeline",
        "video",
    )

    for section in required_sections:
        if section in data:
            result.pass_(f"Section {section}")
        else:
            result.fail(f"Section absente : {section}")

    gpx_value = str(data.get("gpx", {}).get("file", "")).strip()

    if not gpx_value:
        result.fail("gpx.file est vide.")
    else:
        gpx_path = Path(gpx_value)
        if not gpx_path.is_absolute():
            gpx_path = PROJECT_ROOT / gpx_path

        if gpx_path.exists():
            result.pass_(f"GPX : {gpx_path}")
        else:
            result.fail(f"GPX introuvable : {gpx_path}")

    leader = data.get("leader", {})
    for key in (
        "enabled",
        "style",
        "color",
        "radius",
        "z_offset",
        "halo_scale",
        "halo_opacity",
        "trail_enabled",
        "trail_fraction",
        "trail_width",
        "trail_opacity",
    ):
        if key in leader:
            result.pass_(f"leader.{key}")
        else:
            result.warn(f"leader.{key} absent")

    result.pass_(f"Projet contrôlé : {project_file}")
    return result


def check_satellite(project_file: Path | None) -> CheckResult:
    result = CheckResult("Textures satellite")

    if project_file is None:
        result.warn("Contrôle ignoré : aucun projet.")
        return result

    if not project_file.is_absolute():
        project_file = PROJECT_ROOT / project_file

    try:
        data = yaml.safe_load(
            project_file.read_text(encoding="utf-8")
        ) or {}
    except Exception as error:
        result.fail(f"Lecture YAML impossible : {error}")
        return result

    terrain = data.get("terrain", {})
    if not bool(terrain.get("satellite", False)):
        result.pass_("Texture satellite désactivée dans le projet.")
        return result

    gpx_value = str(data.get("gpx", {}).get("file", "")).strip()
    if not gpx_value:
        result.fail("Impossible de déterminer le nom du GPX.")
        return result

    zoom = int(terrain.get("satellite_zoom", 14))
    stem = Path(gpx_value).stem
    cache = PROJECT_ROOT / "cache" / "satellite"

    original = cache / f"{stem}_satellite_z{zoom}.png"
    metadata = cache / f"{stem}_satellite_z{zoom}.json"
    preview = cache / f"{stem}_satellite_z{zoom}_preview.png"
    video = cache / f"{stem}_satellite_z{zoom}_video.png"

    for label, file in (
        ("Mosaïque originale", original),
        ("Métadonnées", metadata),
        ("Texture preview", preview),
        ("Texture vidéo", video),
    ):
        if file.exists():
            size_mb = file.stat().st_size / (1024 * 1024)
            result.pass_(f"{label} : {file.name} ({size_mb:.1f} Mo)")
        elif label in ("Texture preview", "Texture vidéo"):
            result.warn(f"{label} absente : {file.name}")
        else:
            result.fail(f"{label} absente : {file.name}")

    return result


def run_alignment_diagnostic() -> CheckResult:
    result = CheckResult("Diagnostic trace / terrain")
    script = PROJECT_ROOT / "tools" / "diagnostic_trace.py"

    if not script.exists():
        result.warn("tools/diagnostic_trace.py absent.")
        return result

    try:
        process = subprocess.run(
            [sys.executable, str(script)],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=180,
        )
    except Exception as error:
        result.fail(str(error))
        return result

    output = (process.stdout or "") + (process.stderr or "")
    print("\n--- SORTIE DIAGNOSTIC ---")
    print(output.rstrip())
    print("--- FIN DIAGNOSTIC ---")

    if process.returncode != 0:
        result.fail(f"Code retour : {process.returncode}")
    elif "Trace / relief     : OK" in output or "Trace / relief : OK" in output:
        result.pass_("Alignement validé.")
    else:
        result.warn("Le diagnostic s'est terminé sans confirmation explicite OK.")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Contrôles de stabilisation GPX Flyover Studio."
    )
    parser.add_argument(
        "--project",
        help="Projet YAML à contrôler. Par défaut : YAML le plus récent.",
    )
    parser.add_argument(
        "--skip-alignment",
        action="store_true",
        help="Ne pas lancer tools/diagnostic_trace.py.",
    )
    args = parser.parse_args()

    print("===================================")
    print("STABILISATION GPX FLYOVER STUDIO")
    print("===================================")
    print("Racine :", PROJECT_ROOT)

    project_file = locate_project(args.project)
    if project_file:
        print("Projet :", project_file)
    else:
        print("Projet : aucun")

    results = [
        compile_files(),
        import_modules(),
        check_yaml(project_file),
        check_satellite(project_file),
    ]

    if not args.skip_alignment:
        results.append(run_alignment_diagnostic())

    for result in results:
        result.print()

    failures = [result for result in results if not result.ok]

    print("\n===================================")
    if failures:
        print(f"STABILISATION : ÉCHEC ({len(failures)} bloc(s))")
        print("Ne pas faire le tag Git avant correction.")
        return 1

    print("STABILISATION : OK")
    print("La base peut être commitée et taguée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
