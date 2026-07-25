from pathlib import Path

from studio.analyzer import analyze_gpx


def main():
    gpx_file = Path(
        "gpx/31_kagbeni_sangda-24667827-1784704753-767.gpx"
    )

    analysis = analyze_gpx(
        gpx_file
    )

    print()
    print("===================================")
    print("ANALYSE GPX")
    print("===================================")
    print("Nom        :", analysis.name)
    print("Points     :", analysis.point_count)
    print("Distance   :", analysis.distance_km, "km")
    print("D+         :", analysis.ascent_m, "m")
    print("D-         :", analysis.descent_m, "m")
    print(
        "Altitude   :",
        analysis.min_elevation_m,
        "->",
        analysis.max_elevation_m,
        "m",
    )
    print("Relief     :", analysis.relief_index, "/ 100")
    print(
        "Difficulté :",
        analysis.difficulty_index,
        "/ 100 -",
        analysis.difficulty_label,
    )
    print("Terrain    :", analysis.terrain_profile)
    print("Style      :", analysis.suggested_style)
    print("Qualité    :", analysis.suggested_quality)
    print(
        "Durée      :",
        analysis.suggested_duration_seconds,
        "s",
    )
    print("===================================")


if __name__ == "__main__":
    main()
