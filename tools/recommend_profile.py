from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.analysis.analyzer import analyze_gpx
from studio.profiles.engine import ProfileEngine
from studio.profiles.report import print_profile_report


def resolve_gpx(path: Path) -> Path:
    if path.suffix.lower() == ".gpx":
        return path

    if path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError(
            "Fournissez un GPX ou un projet YAML."
        )

    data = yaml.safe_load(
        path.read_text(encoding="utf-8")
    ) or {}

    value = str(
        data.get("gpx", {}).get("file", "")
    ).strip()

    if not value:
        raise ValueError(
            "gpx.file est absent du projet YAML."
        )

    gpx_path = Path(value)

    if not gpx_path.is_absolute():
        gpx_path = ROOT / gpx_path

    return gpx_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Analyse un GPX et propose plusieurs profils "
            "sans modifier le YAML."
        )
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Fichier GPX ou projet YAML.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Nombre de profils affichés.",
    )
    parser.add_argument(
        "--json",
        dest="json_file",
        type=Path,
        help="Enregistre les résultats en JSON.",
    )
    args = parser.parse_args()

    input_file = args.input_file

    if not input_file.is_absolute():
        input_file = ROOT / input_file

    gpx_file = resolve_gpx(input_file)
    metrics = analyze_gpx(gpx_file)

    matches = ProfileEngine().match(metrics)

    print("GPX :", gpx_file)
    print_profile_report(
        matches,
        limit=args.limit,
    )

    if args.json_file:
        output = args.json_file

        if not output.is_absolute():
            output = ROOT / output

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            json.dumps(
                {
                    "gpx_file": str(gpx_file),
                    "metrics": metrics,
                    "profiles": [
                        match.to_dict()
                        for match in matches
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print("Rapport JSON :", output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
