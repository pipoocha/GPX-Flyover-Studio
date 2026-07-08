import config
from studio.camera.presets import (
    get_camera_preset,
    apply_camera_values,
)


class Timeline:
    def __init__(self, total_frames, hold_frames=0, segments=None):
        self.total_frames = total_frames

        # Sécurité : le temps d'arrêt final ne doit jamais prendre toute la vidéo
        self.hold_frames = min(
            hold_frames,
            max(0, total_frames // 3),
        )

        self.moving_frames = max(1, total_frames - self.hold_frames)
        self.segments = segments or []

        self.segment_frames = []
        self._build_segments()

    def _build_segments(self):
        if not self.segments:
            return

        total_duration = sum(float(s.get("duration", 1)) for s in self.segments)
        start = 0

        for segment in self.segments:
            ratio = float(segment.get("duration", 1)) / total_duration
            length = max(1, int(self.moving_frames * ratio))
            end = min(self.moving_frames, start + length)

            self.segment_frames.append(
                {
                    "start": start,
                    "end": end,
                    "preset": str(segment.get("preset", "cinematic")).lower(),
                    "transition": float(segment.get("transition", 0)),
                }
            )

            start = end

        if self.segment_frames:
            self.segment_frames[-1]["end"] = self.moving_frames

    def ease(self, t):
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    def is_hold(self, frame_index):
        return frame_index >= self.moving_frames

    def progress_at(self, frame_index):
        if frame_index >= self.moving_frames:
            return 1.0

        t = frame_index / max(1, self.moving_frames - 1)
        return self.ease(t)

    def segment_at(self, frame_index):
        if not self.segment_frames:
            return None, None

        for i, segment in enumerate(self.segment_frames):
            if segment["start"] <= frame_index < segment["end"]:
                return segment, i

        return self.segment_frames[-1], len(self.segment_frames) - 1

    def blend_presets(self, a, b, t):
        t = self.ease(t)

        values = {}

        for key in a:
            values[key] = a[key] * (1 - t) + b[key] * t

        return values

    def apply_camera_at(self, frame_index, fps):
        segment, index = self.segment_at(frame_index)

        if segment is None:
            return None

        preset_name = segment["preset"]
        current = get_camera_preset(preset_name)

        if index == 0:
            apply_camera_values(current, config)
            return preset_name

        previous_segment = self.segment_frames[index - 1]
        previous = get_camera_preset(previous_segment["preset"])

        transition_seconds = segment.get("transition", 0)
        transition_frames = int(transition_seconds * fps)

        if transition_frames <= 0:
            apply_camera_values(current, config)
            return preset_name

        local_frame = frame_index - segment["start"]

        if local_frame >= transition_frames:
            apply_camera_values(current, config)
            return preset_name

        blend = local_frame / max(1, transition_frames)
        values = self.blend_presets(previous, current, blend)

        apply_camera_values(values, config)

        return f"{previous_segment['preset']} → {preset_name}"