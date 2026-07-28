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
    "footprint_fill_ratio": ("Remplissage de l'emprise", ""),
    "footprint_max_span_km": ("Portée maximale réelle", "km"),
    "footprint_elongation_ratio": ("Allongement de l'emprise", ""),
    "route_density_km_per_km2": ("Densité du parcours", "km/km²"),
    "turn_angle_mean_deg": ("Angle moyen des virages", "°"),
    "turn_angle_median_deg": ("Angle médian des virages", "°"),
    "sharp_turn_ratio_percent": ("Virages très marqués", "%"),
    "medium_turn_ratio_percent": ("Virages marqués", "%"),
    "overlap_10m_percent": ("Recouvrement à 10 m", "%"),
    "overlap_20m_percent": ("Recouvrement à 20 m", "%"),
    "overlap_40m_percent": ("Recouvrement à 40 m", "%"),
    "maximum_pass_count_20m": ("Passages max dans une zone de 20 m", ""),
    "mean_pass_count_20m": ("Passages moyens à 20 m", ""),
    "closure_index_percent": ("Indice de fermeture", "%"),
    "overlap_index_percent": ("Indice de recouvrement", "%"),
    "repetition_index_percent": ("Indice de répétition", "%"),
    "linearity_index_percent": ("Indice de linéarité", "%"),
    "compactness_index_percent": ("Indice de compacité", "%"),
    "occupied_area_25m_km2": ("Surface réellement occupée 25 m", "km²"),
    "occupied_cells_25m": ("Cellules occupées 25 m", ""),
    "revisited_cells_25m_percent": ("Cellules revisitées 25 m", "%"),
    "maximum_cell_visits_25m": ("Passages max par cellule 25 m", ""),
    "mean_cell_visits_25m": ("Passages moyens par cellule 25 m", ""),
    "occupied_area_50m_km2": ("Surface réellement occupée 50 m", "km²"),
    "radius_mean_km": ("Rayon moyen", "km"),
    "radius_median_km": ("Rayon médian", "km"),
    "radius_max_km": ("Rayon maximal", "km"),
    "dominant_orientation_deg": ("Orientation dominante", "°"),
    "occupation_index_percent": ("Occupation du corridor", "%"),
    "occupation_level": ("Densité du corridor", ""),
    "span_distance_ratio": ("Rapport portée/distance", ""),
    "footprint_level": ("Compacité de l'emprise", ""),
    "recommended_terrain_width_km": ("Largeur terrain conseillée", "km"),
    "recommended_terrain_height_km": ("Hauteur terrain conseillée", "km"),
    "recommended_terrain_margin_m": ("Marge terrain conseillée", "m"),
    "altitude_min_m": ("Altitude minimale", "m"),
    "altitude_max_m": ("Altitude maximale", "m"),
    "altitude_amplitude_m": ("Amplitude altimétrique", "m"),
    "elevation_gain_m": ("Dénivelé positif", "m"),
    "elevation_loss_m": ("Dénivelé négatif", "m"),
    "grade_mean_percent": ("Pente moyenne absolue", "%"),
    "grade_median_percent": ("Pente médiane absolue", "%"),
    "grade_max_percent": ("Pente maximale locale", "%"),
    "relief_index_percent": ("Indice synthétique de relief", "%"),
    "relief_level": ("Niveau de relief", ""),
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
    print("ANALYSE DU PARCOURS — AIP V5.6 A3.6")
    print("=" * 64)
    print("Source :", result["source_file"])
    print()

    for key, (label, unit) in LABELS.items():
        value = result.get(key)

        if value is None:
            text = "indisponible"
        elif isinstance(value, int):
            text = str(value)
        elif isinstance(value, str):
            text = value
        else:
            text = f"{float(value):.3f}"

        suffix = f" {unit}" if unit else ""
        print(f"{label:<31} {text}{suffix}")

    print()
    print("=" * 64)
    print("SYNTHÈSE DES CARACTÉRISTIQUES")
    print("=" * 64)

    closure = float(result.get("closure_index_percent", 0.0))
    linearity = float(result.get("linearity_index_percent", 0.0))
    repetition = float(result.get("repetition_index_percent", 0.0))

    overlap = float(result.get("overlap_index_percent", 0.0))

    if closure >= 85.0 and overlap < 15.0:
        closure_text = "boucle fermée"
    elif closure >= 85.0 and repetition < 35.0:
        closure_text = "boucle avec quelques recroisements"
    elif closure >= 85.0:
        closure_text = "circuit fortement répété"
    elif linearity >= 65.0:
        closure_text = "étape principalement en ligne"
    else:
        closure_text = "parcours ouvert ou mixte"

    print(f"Structure dominante             {closure_text}")
    print(
        "Compacité de l'emprise         "
        f"{result.get('footprint_level', 'indisponible')}"
    )
    print(
        "Densité du corridor            "
        f"{result.get('occupation_level', 'indisponible')}"
    )
    print(
        "Niveau de relief               "
        f"{result.get('relief_level', 'indisponible')}"
    )
    print(
        "Terrain conseillé              "
        f"{result.get('recommended_terrain_width_km', 0):.0f} x "
        f"{result.get('recommended_terrain_height_km', 0):.0f} km"
    )
    print(
        "Orientation dominante          "
        f"{result.get('dominant_orientation_deg', 0.0):.1f}°"
    )
    print()
    print("Aucune recommandation de profil ni modification du YAML à cette étape.")
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
