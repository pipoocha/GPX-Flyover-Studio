from dataclasses import dataclass

import config


@dataclass
class TrackConfig:
    radius: int = 7
    sides: int = 8
    progressive: bool = True
    update_every: int = 15

    def apply(self):
        config.TRACK_RADIUS = self.radius
        config.TRACK_SIDES = self.sides
        config.TRACE_PROGRESSIVE = self.progressive
        config.TRACE_UPDATE_EVERY = self.update_every