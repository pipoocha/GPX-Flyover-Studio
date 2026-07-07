from config.version import VERSION

from config.settings import (
    MODE,
    VIDEO_DURATION,
    FINAL_HOLD_SECONDS,
    FPS,
    TOTAL_FRAMES,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    CAMERA_HEIGHT,
    CAMERA_DISTANCE,
    LOOK_AHEAD,
    CAMERA_SMOOTHING,
    FOCAL_HEIGHT,
    SIDE_OFFSET,
    TRACK_RADIUS,
    TRACK_SIDES,
    TRACK_RENDER_MODE,
    TRACE_PROGRESSIVE,
    TRACE_UPDATE_EVERY,
    USE_SATELLITE,
    TIMELINE,
    PROJECT_TITLE,
)

from config.paths import (
    ROOT_DIR,
    GPX_DIR,
    CACHE_DIR,
    FRAMES_DIR,
    TILES_DIR,
    OUTPUT_DIR,
    VIDEO_DIR,
    LOG_DIR,
    DEFAULT_GPX,
    DEFAULT_VIDEO,
    create_directories,
)