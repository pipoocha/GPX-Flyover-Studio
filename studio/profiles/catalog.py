from __future__ import annotations

from studio.profiles.models import ProfileDefinition


PROFILE_CATALOG = (
    ProfileDefinition(
        key="plaine_compacte",
        label="Plaine compacte",
        description=(
            "Parcours peu accidenté, fermé ou compact, "
            "sur une emprise réduite."
        ),
        rules={
            "relief_index_percent": {"max": 24.0, "weight": 1.5},
            "closure_index_percent": {"min": 60.0, "weight": 0.8},
            "compactness_index_percent": {"min": 50.0, "weight": 1.0},
            "linearity_index_percent": {"max": 35.0, "weight": 0.7},
            "repetition_index_percent": {"max": 20.0, "weight": 0.5},
        },
        base_settings={
            "camera.distance.minimum": 650,
            "camera.distance.maximum": 2100,
            "camera.height.minimum": 300,
            "camera.height.maximum": 950,
            "camera.look_ahead": 220,
            "camera.smoothing": 0.12,
            "terrain.max_cells": 50000,
            "terrain.satellite_zoom": 17,
            "timeline.travel_seconds_per_km": 1.15,
        },
    ),
    ProfileDefinition(
        key="plaine_ligne",
        label="Plaine — étape en ligne",
        description=(
            "Parcours peu accidenté et principalement linéaire."
        ),
        rules={
            "relief_index_percent": {"max": 24.0, "weight": 1.5},
            "linearity_index_percent": {"min": 55.0, "weight": 1.3},
            "closure_index_percent": {"max": 55.0, "weight": 0.8},
            "footprint_elongation_ratio": {"min": 1.6, "weight": 0.8},
        },
        base_settings={
            "camera.distance.minimum": 900,
            "camera.distance.maximum": 3000,
            "camera.height.minimum": 450,
            "camera.height.maximum": 1250,
            "camera.look_ahead": 320,
            "camera.smoothing": 0.15,
            "terrain.max_cells": 48000,
            "terrain.satellite_zoom": 16,
            "timeline.travel_seconds_per_km": 1.00,
        },
    ),
    ProfileDefinition(
        key="vallonne_compact",
        label="Vallonné compact",
        description=(
            "Relief modéré, boucle ou parcours compact, "
            "avec variations régulières."
        ),
        rules={
            "relief_index_percent": {
                "min": 20.0,
                "max": 43.0,
                "weight": 1.5,
            },
            "closure_index_percent": {"min": 55.0, "weight": 0.8},
            "compactness_index_percent": {"min": 45.0, "weight": 0.9},
            "repetition_index_percent": {"max": 25.0, "weight": 0.5},
        },
        base_settings={
            "camera.distance.minimum": 800,
            "camera.distance.maximum": 2600,
            "camera.height.minimum": 420,
            "camera.height.maximum": 1250,
            "camera.look_ahead": 260,
            "camera.smoothing": 0.11,
            "terrain.max_cells": 58000,
            "terrain.satellite_zoom": 17,
            "timeline.travel_seconds_per_km": 1.25,
        },
    ),
    ProfileDefinition(
        key="moyenne_montagne_compacte",
        label="Moyenne montagne — boucle compacte",
        description=(
            "Relief soutenu, faible recouvrement et emprise compacte."
        ),
        rules={
            "relief_index_percent": {
                "min": 40.0,
                "max": 64.0,
                "weight": 1.7,
            },
            "closure_index_percent": {"min": 75.0, "weight": 1.0},
            "compactness_index_percent": {"min": 50.0, "weight": 1.0},
            "repetition_index_percent": {"max": 18.0, "weight": 0.8},
            "linearity_index_percent": {"max": 30.0, "weight": 0.5},
        },
        base_settings={
            "camera.distance.minimum": 900,
            "camera.distance.maximum": 3000,
            "camera.height.minimum": 500,
            "camera.height.maximum": 1500,
            "camera.look_ahead": 280,
            "camera.smoothing": 0.10,
            "terrain.max_cells": 65000,
            "terrain.satellite_zoom": 18,
            "timeline.travel_seconds_per_km": 1.35,
        },
    ),
    ProfileDefinition(
        key="moyenne_montagne_ligne",
        label="Moyenne montagne — traversée",
        description=(
            "Relief soutenu et parcours ouvert ou allongé."
        ),
        rules={
            "relief_index_percent": {
                "min": 38.0,
                "max": 65.0,
                "weight": 1.7,
            },
            "linearity_index_percent": {"min": 42.0, "weight": 1.0},
            "closure_index_percent": {"max": 70.0, "weight": 0.6},
            "footprint_elongation_ratio": {"min": 1.35, "weight": 0.7},
        },
        base_settings={
            "camera.distance.minimum": 1100,
            "camera.distance.maximum": 3600,
            "camera.height.minimum": 650,
            "camera.height.maximum": 1850,
            "camera.look_ahead": 340,
            "camera.smoothing": 0.13,
            "terrain.max_cells": 62000,
            "terrain.satellite_zoom": 17,
            "timeline.travel_seconds_per_km": 1.20,
        },
    ),
    ProfileDefinition(
        key="haute_montagne_compacte",
        label="Haute montagne — boucle compacte",
        description=(
            "Relief très marqué, emprise compacte et parcours fermé."
        ),
        rules={
            "relief_index_percent": {"min": 62.0, "weight": 1.8},
            "closure_index_percent": {"min": 70.0, "weight": 0.9},
            "compactness_index_percent": {"min": 45.0, "weight": 0.9},
            "repetition_index_percent": {"max": 25.0, "weight": 0.5},
        },
        base_settings={
            "camera.distance.minimum": 1150,
            "camera.distance.maximum": 3900,
            "camera.height.minimum": 700,
            "camera.height.maximum": 2300,
            "camera.look_ahead": 300,
            "camera.smoothing": 0.09,
            "terrain.max_cells": 76000,
            "terrain.satellite_zoom": 18,
            "timeline.travel_seconds_per_km": 1.45,
        },
    ),
    ProfileDefinition(
        key="haute_montagne_traversee",
        label="Haute montagne — grande traversée",
        description=(
            "Relief très marqué et emprise étendue ou linéaire."
        ),
        rules={
            "relief_index_percent": {"min": 62.0, "weight": 1.8},
            "linearity_index_percent": {"min": 35.0, "weight": 0.8},
            "footprint_elongation_ratio": {"min": 1.3, "weight": 0.7},
            "closure_index_percent": {"max": 80.0, "weight": 0.5},
        },
        base_settings={
            "camera.distance.minimum": 1400,
            "camera.distance.maximum": 4800,
            "camera.height.minimum": 900,
            "camera.height.maximum": 2900,
            "camera.look_ahead": 380,
            "camera.smoothing": 0.12,
            "terrain.max_cells": 72000,
            "terrain.satellite_zoom": 17,
            "timeline.travel_seconds_per_km": 1.30,
        },
    ),
    ProfileDefinition(
        key="circuit_repete",
        label="Circuit répété",
        description=(
            "Nombreux passages dans la même zone, petite emprise "
            "et répétition importante."
        ),
        rules={
            "repetition_index_percent": {"min": 38.0, "weight": 1.8},
            "overlap_index_percent": {"min": 30.0, "weight": 1.3},
            "closure_index_percent": {"min": 65.0, "weight": 0.7},
            "compactness_index_percent": {"min": 45.0, "weight": 0.6},
        },
        base_settings={
            "camera.distance.minimum": 400,
            "camera.distance.maximum": 1600,
            "camera.height.minimum": 250,
            "camera.height.maximum": 750,
            "camera.look_ahead": 140,
            "camera.smoothing": 0.16,
            "terrain.max_cells": 42000,
            "terrain.satellite_zoom": 18,
            "timeline.travel_seconds_per_km": 0.90,
        },
    ),
)
