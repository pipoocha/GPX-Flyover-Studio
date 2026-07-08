TRACK_PRESETS = {
    "fast": {
        "radius": 7,
        "sides": 8,
        "render_mode": "line",
        "progressive": True,
        "update_every": 5,
    },
    "quality": {
        "radius": 8,
        "sides": 12,
        "render_mode": "tube",
        "progressive": True,
        "update_every": 10,
    },
    "ultra": {
        "radius": 8,
        "sides": 24,
        "render_mode": "tube",
        "progressive": True,
        "update_every": 15,
    },
}


def get_track_preset(name):
    preset = TRACK_PRESETS.get(name)

    if preset is None:
        raise ValueError(
            f"Preset trace inconnu : {name}. "
            f"Disponibles : {', '.join(TRACK_PRESETS.keys())}"
        )

    return preset.copy()