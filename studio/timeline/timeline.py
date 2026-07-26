from __future__ import annotations


class TimelineMapper:
    """Convertit la progression linéaire en progression ralentie au départ et à l'arrivée."""

    def __init__(self, timeline_config):
        self.config = timeline_config

    @staticmethod
    def smoothstep(value):
        value = max(0.0, min(1.0, float(value)))
        return value * value * (3.0 - 2.0 * value)

    def travel_progress(self, linear_progress):
        linear = max(0.0, min(1.0, float(linear_progress)))
        travel = max(0.001, float(self.config.effective_travel))
        start_ratio = min(0.35, max(0.0, float(self.config.slowdown_start) / travel))
        end_ratio = min(0.35, max(0.0, float(self.config.slowdown_end) / travel))

        if start_ratio > 0 and linear < start_ratio:
            local = linear / start_ratio
            return start_ratio * self.smoothstep(local)

        if end_ratio > 0 and linear > 1.0 - end_ratio:
            local = (linear - (1.0 - end_ratio)) / end_ratio
            return (1.0 - end_ratio) + end_ratio * self.smoothstep(local)

        return linear
