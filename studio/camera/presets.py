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
    "panorama": {
        "height": 3600,
        "distance": 6500,
        "look_ahead": 800,
        "smoothing": 100,
        "focal_height": 500,
        "side_offset": 1100,
    },
    "arrival": {
        "height": 1300,
        "distance": 2500,
        "look_ahead": 300,
        "smoothing": 40,
        "focal_height": 220,
        "side_offset": 250,
    },
}


def get_camera_preset(name):
    preset = CAMERA_PRESETS.get(name)

    if preset is None:
        raise ValueError(
            f"Preset caméra inconnu : {name}. "
            f"Disponibles : {', '.join(CAMERA_PRESETS.keys())}"
        )

    return preset.copy()


def apply_camera_values(values, config):
    config.CAMERA_HEIGHT = int(values["height"])
    config.CAMERA_DISTANCE = int(values["distance"])
    config.LOOK_AHEAD = int(values["look_ahead"])
    config.CAMERA_SMOOTHING = int(values["smoothing"])
    config.FOCAL_HEIGHT = int(values["focal_height"])
    config.SIDE_OFFSET = int(values["side_offset"])


def apply_camera_preset(name, config):
    apply_camera_values(
        get_camera_preset(name),
        config,
    )