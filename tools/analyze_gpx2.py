from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.analysis.analyzer import analyze_gpx


LABELS = {
    "point_count": ("Nombre de points", ""),
    "distance_total_km": ("Distance totale", "km"),
    "distance_start_end_km": ("Distance départ-arrivée", "km"),
    "start_end_ratio": ("Rapport direct/parcouru", ""),
    "footprint_width_km": ("Largeur de l'emprise", "km"),
    "footprint_height_km": ("Hauteur de l'emprise", "km"),
    "footprint_bbox_area_km2": ("Surface boîte englobante", "km²"),
    "footprint_hull_area_km2": ("Surface enveloppe convexe", "km²"),
    "altitude_min_m": ("Altitude minimale", "m"),
    "altitude_max_m": ("Altitude maximale", "m"),
    "altitude_amplitude_m": ("Amplitude altimétrique", "m"),
    "elevation_gain_m": ("Dénivelé positif", "m"),
    "elevation_loss_m": ("Dénivelé négatif", "m"),
    "grade_mean_percent": ("Pente moyenne absolue", "%"),
    "grade_median_percent": ("Pente médiane absolue", "%"),
    "grade_max_percent": ("Pente maximale locale", "%"),
    "spacing_mean_m": ("Espacement moyen", "m"),
    "spacing_median_m": ("Espacement médian", "m"),
    "spacing_min_m": ("Espacement minimal", "m"),
    "spacing_max_m": ("Espacement maximal", "m"),
    "point_density_per_km": ("Densité de points", "points/km"),
    "elevation_completeness_percent": ("Altitudes présentes", "%"),
    "geometry_confidence_percent": ("Confiance géométrie", "%"),
    "relief_confidence_percent": ("Confiance relief", "%"),
}


def resolve_gpx(path):
    path = Path(path)

    if path.suffix.lower() == ".gpx":
        return path

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    value = str(data.get("gpx", {}).get("file", "")).strip()

    if not value:
        raise ValueError("gpx.file absent du YAML.")

    candidate = Path(value)
    return candidate if candidate.is_absolute() else ROOT / candidate


def display(result):
    print("=" * 64)
    print("ANALYSE DU PARCOURS — AIP V5.6 A1")
    print("=" * 64)
    print("Source :", result["source_file"])
    print()

    for key, (label, unit) in LABELS.items():
        value = result.get(key)

        if value is None:
            text = "indisponible"
        elif isinstance(value, int):
            text = str(value)
        else:
            text = f"{float(value):.3f}"

        suffix = f" {unit}" if unit else ""
        print(f"{label:<31} {text}{suffix}")

    print()
    print("Aucune recommandation ni modification du YAML à cette étape.")
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--json", dest="json_file", type=Path)
    args = parser.parse_args()

    input_file = args.input_file
    if not input_file.is_absolute():
        input_file = ROOT / input_file

    result = analyze_gpx(resolve_gpx(input_file))
    display(result)

    if args.json_file:
        output = args.json_file
        if not output.is_absolute():
            output = ROOT / output

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print("Rapport JSON :", output)


if __name__ == "__main__":
    main()
