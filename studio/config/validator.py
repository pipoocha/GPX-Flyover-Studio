from __future__ import annotations

import re

from studio.config.models import ProjectConfig


class ConfigValidationError(ValueError):
    pass


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validate_project(project: ProjectConfig, require_existing_gpx: bool = False) -> None:
    errors: list[str] = []

    if not project.title.strip():
        errors.append("Le titre du projet est vide.")

    if not str(project.gpx.file).strip():
        errors.append("Le fichier GPX n'est pas renseigné.")
    elif require_existing_gpx and not project.gpx.file.exists():
        errors.append(f"GPX introuvable : {project.gpx.file}")

    for name, camera_range in (
        ("distance", project.camera.distance),
        ("hauteur", project.camera.height),
        ("latéral", project.camera.lateral),
    ):
        if camera_range.minimum < 0:
            errors.append(f"Caméra {name} : minimum négatif.")
        if camera_range.maximum <= camera_range.minimum:
            errors.append(f"Caméra {name} : maximum doit être supérieur au minimum.")
        if camera_range.scale <= 0:
            errors.append(f"Caméra {name} : échelle doit être positive.")

    if not 0.0 < project.camera.smoothing <= 1.0:
        errors.append("Le lissage caméra doit être compris entre 0 et 1.")

    if project.camera.look_ahead < 1:
        errors.append("L'anticipation caméra doit être positive.")

    if not HEX_COLOR.match(project.track.color):
        errors.append("La couleur de trace doit être au format #RRGGBB.")

    if project.track.width <= 0:
        errors.append("La largeur de trace doit être positive.")

    if project.track.z_offset < 0:
        errors.append("Le décalage vertical de la trace ne peut pas être négatif.")

    if project.terrain.source not in {"copernicus", "srtm"}:
        errors.append("Source terrain autorisée : copernicus ou srtm.")

    if not 1 <= project.terrain.satellite_zoom <= 19:
        errors.append("Le zoom satellite doit être compris entre 1 et 19.")

    if project.terrain.max_cells < 10000:
        errors.append("Le nombre maximal de cellules doit être au moins 10000.")

    for name, value in project.timeline.to_dict().items():
        if value < 0:
            errors.append(f"Timeline {name} : durée négative.")

    if project.timeline.travel <= 0:
        errors.append("La durée de parcours doit être positive.")

    if not 1 <= project.video.fps <= 120:
        errors.append("Les FPS doivent être compris entre 1 et 120.")

    if project.video.width < 320 or project.video.height < 240:
        errors.append("Résolution vidéo trop faible.")

    if project.video.mode not in {"PREVIEW", "VIDEO"}:
        errors.append("Mode vidéo autorisé : PREVIEW ou VIDEO.")

    if errors:
        raise ConfigValidationError("\n".join(f"- {error}" for error in errors))
