CAMERA_PRESETS = {
    "drone": {
        "height": 2200,
        "distance": 4200,
        "look_ahead": 500,
        "smoothing": 60,
        "focal_height": 300,
        "side_offset": 250,
    },

    "cinematic": {
        "height": 1700,
        "distance": 3600,
        "look_ahead": 420,
        "smoothing": 45,
        "focal_height": 260,
        "side_offset": 450,
    },

    "chase": {
        "height": 900,
        "distance": 1800,
        "look_ahead": 260,
        "smoothing": 30,
        "focal_height": 160,
        "side_offset": 150,
    },

    "helicopter": {
        "height": 3000,
        "distance": 5200,
        "look_ahead": 650,
        "smoothing": 80,
        "focal_height": 400,
        "side_offset": 700,
    },
}


def apply_camera_preset(name, config):
    preset = CAMERA_PRESETS.get(name)

    if preset is None:
        raise ValueError(
            f"Preset caméra inconnu : {name}. "
            f"Disponibles : {', '.join(CAMERA_PRESETS.keys())}"
        )

    config.CAMERA_HEIGHT = preset["height"]
    config.CAMERA_DISTANCE = preset["distance"]
    config.LOOK_AHEAD = preset["look_ahead"]
    config.CAMERA_SMOOTHING = preset["smoothing"]
    config.FOCAL_HEIGHT = preset["focal_height"]
    config.SIDE_OFFSET = preset["side_offset"]