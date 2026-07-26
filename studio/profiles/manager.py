from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import re

import yaml


class ProfileManager:
    """Profils de terrain et styles de caméra pour l'interface V6."""

    TERRAIN_PROFILES = {
        "Plaine": {
            "distance_min": 450.0, "distance_max": 1700.0, "distance_scale": 0.18,
            "height_min": 180.0, "height_max": 700.0, "height_scale": 0.08,
            "lateral_min": 20.0, "lateral_max": 180.0, "lateral_scale": 0.04,
            "look_ahead": 130, "smoothing": 0.08,
            "terrain_margin": 0.020, "terrain_max_cells": 70000, "terrain_zoom": 15,
        },
        "Collines": {
            "distance_min": 650.0, "distance_max": 2200.0, "distance_scale": 0.24,
            "height_min": 280.0, "height_max": 1000.0, "height_scale": 0.11,
            "lateral_min": 40.0, "lateral_max": 260.0, "lateral_scale": 0.06,
            "look_ahead": 165, "smoothing": 0.08,
            "terrain_margin": 0.018, "terrain_max_cells": 85000, "terrain_zoom": 15,
        },
        "Moyenne montagne": {
            "distance_min": 850.0, "distance_max": 2850.0, "distance_scale": 0.30,
            "height_min": 420.0, "height_max": 1400.0, "height_scale": 0.15,
            "lateral_min": 60.0, "lateral_max": 330.0, "lateral_scale": 0.07,
            "look_ahead": 200, "smoothing": 0.09,
            "terrain_margin": 0.017, "terrain_max_cells": 100000, "terrain_zoom": 14,
        },
        "Haute montagne": {
            "distance_min": 1050.0, "distance_max": 3500.0, "distance_scale": 0.37,
            "height_min": 580.0, "height_max": 1850.0, "height_scale": 0.19,
            "lateral_min": 75.0, "lateral_max": 400.0, "lateral_scale": 0.08,
            "look_ahead": 230, "smoothing": 0.10,
            "terrain_margin": 0.016, "terrain_max_cells": 125000, "terrain_zoom": 14,
        },
        "Alpes": {
            "distance_min": 1000.0, "distance_max": 3350.0, "distance_scale": 0.35,
            "height_min": 540.0, "height_max": 1750.0, "height_scale": 0.18,
            "lateral_min": 70.0, "lateral_max": 380.0, "lateral_scale": 0.08,
            "look_ahead": 220, "smoothing": 0.10,
            "terrain_margin": 0.017, "terrain_max_cells": 130000, "terrain_zoom": 15,
        },
        "Pyrénées": {
            "distance_min": 900.0, "distance_max": 3100.0, "distance_scale": 0.33,
            "height_min": 480.0, "height_max": 1600.0, "height_scale": 0.17,
            "lateral_min": 60.0, "lateral_max": 340.0, "lateral_scale": 0.07,
            "look_ahead": 205, "smoothing": 0.09,
            "terrain_margin": 0.018, "terrain_max_cells": 120000, "terrain_zoom": 15,
        },
        "Himalaya": {
            "distance_min": 1200.0, "distance_max": 4100.0, "distance_scale": 0.41,
            "height_min": 680.0, "height_max": 2250.0, "height_scale": 0.22,
            "lateral_min": 85.0, "lateral_max": 430.0, "lateral_scale": 0.08,
            "look_ahead": 250, "smoothing": 0.10,
            "terrain_margin": 0.016, "terrain_max_cells": 150000, "terrain_zoom": 14,
        },
        "Désert": {
            "distance_min": 850.0, "distance_max": 3200.0, "distance_scale": 0.31,
            "height_min": 400.0, "height_max": 1450.0, "height_scale": 0.14,
            "lateral_min": 55.0, "lateral_max": 300.0, "lateral_scale": 0.06,
            "look_ahead": 220, "smoothing": 0.09,
            "terrain_margin": 0.022, "terrain_max_cells": 95000, "terrain_zoom": 15,
        },
        "Glacier": {
            "distance_min": 1150.0, "distance_max": 3900.0, "distance_scale": 0.39,
            "height_min": 650.0, "height_max": 2100.0, "height_scale": 0.21,
            "lateral_min": 70.0, "lateral_max": 360.0, "lateral_scale": 0.07,
            "look_ahead": 245, "smoothing": 0.10,
            "terrain_margin": 0.018, "terrain_max_cells": 145000, "terrain_zoom": 14,
        },
    }

    STYLE_PROFILES = {
        "Tour de France": {"camera_mode": "director", "orientation": "route", "lateral_factor": 0.70, "height_factor": 0.88, "look_factor": 0.85},
        "Cinéma": {"camera_mode": "director", "orientation": "auto", "lateral_factor": 0.90, "height_factor": 1.05, "look_factor": 1.00},
        "Drone": {"camera_mode": "flyover", "orientation": "route", "lateral_factor": 0.45, "height_factor": 0.65, "look_factor": 0.70},
        "Google Earth": {"camera_mode": "director", "orientation": "north", "lateral_factor": 0.35, "height_factor": 1.25, "look_factor": 1.10},
        "Hélicoptère": {"camera_mode": "director", "orientation": "route", "lateral_factor": 0.75, "height_factor": 0.95, "look_factor": 0.90},
    }

    QUALITY_PROFILES = {
        "Rapide": {"cells_factor": 0.55, "fps": 20, "resolution": "854x480"},
        "Standard": {"cells_factor": 0.80, "fps": 20, "resolution": "1280x720"},
        "Haute": {"cells_factor": 1.00, "fps": 30, "resolution": "1920x1080"},
        "Ultra": {"cells_factor": 1.30, "fps": 30, "resolution": "2560x1440"},
    }

    USER_PROFILE_DIR = Path("profiles/user")

    @classmethod
    def ensure_user_profile_dir(cls) -> Path:
        cls.USER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        return cls.USER_PROFILE_DIR

    @staticmethod
    def slugify(name: str) -> str:
        table = str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc")
        value = name.strip().lower().translate(table)
        value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
        return value or "profil_personnalise"

    @classmethod
    def profile_path(cls, name: str) -> Path:
        return cls.ensure_user_profile_dir() / f"{cls.slugify(name)}.yaml"

    @classmethod
    def list_user_profiles(cls) -> list[str]:
        names=[]
        for path in sorted(cls.ensure_user_profile_dir().glob("*.yaml")):
            try:
                data=yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                names.append(str(data.get("metadata",{}).get("name") or path.stem))
            except Exception:
                names.append(path.stem)
        return names

    @classmethod
    def find_user_profile(cls, name: str) -> Path | None:
        direct=cls.profile_path(name)
        if direct.exists(): return direct
        for path in cls.ensure_user_profile_dir().glob("*.yaml"):
            try:
                data=yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if str(data.get("metadata",{}).get("name", "")) == name:
                    return path
            except Exception:
                pass
        return None

    @classmethod
    def save_user_profile(cls, name: str, description: str, settings: dict) -> Path:
        if not name.strip(): raise ValueError("Le nom du profil est obligatoire.")
        target=cls.profile_path(name)
        now=datetime.now().isoformat(timespec="seconds")
        created_at=now; use_count=0
        if target.exists():
            existing=yaml.safe_load(target.read_text(encoding="utf-8")) or {}
            meta=existing.get("metadata",{})
            created_at=str(meta.get("created_at",now)); use_count=int(meta.get("use_count",0))
        payload={"metadata":{"name":name.strip(),"description":description.strip(),"created_at":created_at,"updated_at":now,"use_count":use_count},"settings":deepcopy(settings)}
        target.write_text(yaml.safe_dump(payload,allow_unicode=True,sort_keys=False),encoding="utf-8")
        return target

    @classmethod
    def load_user_profile(cls, name: str) -> dict:
        path=cls.find_user_profile(name)
        if path is None: raise FileNotFoundError(f"Profil utilisateur introuvable : {name}")
        payload=yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        meta=payload.setdefault("metadata",{})
        meta["use_count"]=int(meta.get("use_count",0))+1
        meta["last_used_at"]=datetime.now().isoformat(timespec="seconds")
        path.write_text(yaml.safe_dump(payload,allow_unicode=True,sort_keys=False),encoding="utf-8")
        settings=payload.get("settings",{})
        if not isinstance(settings,dict): raise ValueError(f"Profil utilisateur invalide : {name}")
        return deepcopy(settings)

    @classmethod
    def delete_user_profile(cls, name: str) -> None:
        path=cls.find_user_profile(name)
        if path is None: raise FileNotFoundError(f"Profil utilisateur introuvable : {name}")
        path.unlink()

    @classmethod
    def profile_description(cls, name: str) -> str:
        path=cls.find_user_profile(name)
        if path is None: return ""
        payload=yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return str(payload.get("metadata",{}).get("description", ""))

    @classmethod
    def build(cls, terrain: str, style: str, quality: str) -> dict:
        result = deepcopy(cls.TERRAIN_PROFILES[terrain])
        style_data = cls.STYLE_PROFILES[style]
        quality_data = cls.QUALITY_PROFILES[quality]

        result["camera_mode"] = style_data["camera_mode"]
        result["orientation"] = style_data["orientation"]
        result["lateral_min"] *= style_data["lateral_factor"]
        result["lateral_max"] *= style_data["lateral_factor"]
        result["lateral_scale"] *= style_data["lateral_factor"]
        result["height_min"] *= style_data["height_factor"]
        result["height_max"] *= style_data["height_factor"]
        result["height_scale"] *= style_data["height_factor"]
        result["look_ahead"] = int(result["look_ahead"] * style_data["look_factor"])
        result["terrain_max_cells"] = int(result["terrain_max_cells"] * quality_data["cells_factor"])
        result["fps"] = quality_data["fps"]
        result["resolution"] = quality_data["resolution"]
        return result
