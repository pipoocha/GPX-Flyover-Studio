class Timeline:
    def __init__(self, total_frames, hold_frames=0):
        self.total_frames = total_frames
        self.hold_frames = hold_frames
        self.moving_frames = max(1, total_frames - hold_frames)

    def progress_at(self, frame_index):
        if frame_index >= self.moving_frames:
            return 1.0

        t = frame_index / max(1, self.moving_frames - 1)

        return t * t * (3 - 2 * t)

    def is_hold(self, frame_index):
        return frame_index >= self.moving_frames