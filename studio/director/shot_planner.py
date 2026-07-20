class ShotPlanner:
    def __init__(self):
        self.segments = [
            {
                "name": "reveal",
                "start": 0.00,
                "end": 0.15,
            },
            {
                "name": "follow",
                "start": 0.15,
                "end": 0.55,
            },
            {
                "name": "helicopter",
                "start": 0.55,
                "end": 0.85,
            },
            {
                "name": "finish",
                "start": 0.85,
                "end": 1.00,
            },
        ]

        self.transition_size = 0.035

    @staticmethod
    def clamp(value):
        return max(0.0, min(1.0, value))

    def segment_index_at(self, progress):
        progress = self.clamp(progress)

        for index, segment in enumerate(self.segments):
            if segment["start"] <= progress < segment["end"]:
                return index

        return len(self.segments) - 1

    def plan_at(self, progress):
        progress = self.clamp(progress)
        index = self.segment_index_at(progress)
        segment = self.segments[index]

        segment_length = max(
            1e-9,
            segment["end"] - segment["start"],
        )

        local_progress = (
            progress - segment["start"]
        ) / segment_length

        previous_name = None
        transition = 1.0

        if index > 0:
            transition_end = (
                segment["start"]
                + self.transition_size
            )

            if progress < transition_end:
                previous_name = self.segments[index - 1]["name"]

                transition = (
                    progress - segment["start"]
                ) / self.transition_size

        return {
            "name": segment["name"],
            "previous_name": previous_name,
            "local_progress": self.clamp(local_progress),
            "transition": self.clamp(transition),
        }