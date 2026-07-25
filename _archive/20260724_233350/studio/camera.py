class Camera:
    def __init__(self, xs, ys, config):
        self.xs = xs
        self.ys = ys
        self.config = config

    def cfg(self, *keys, default=None):
        return self.config.get(*keys, default=default)

    def route_size(self):
        width = max(self.xs) - min(self.xs)
        height = max(self.ys) - min(self.ys)
        return max(width, height)

    def frame_count(self):
        duration = self.cfg("video", "duration", default=10)
        fps = self.cfg("video", "fps", default=15)
        return int(duration * fps)

    def generate(self):
        frames = self.frame_count()

        mode = self.cfg("camera", "mode", default="smart")
        zoom_factor = self.cfg("camera", "zoom_factor", default=1.10)
        smoothness = self.cfg("camera", "smoothness", default=0.94)
        look_ahead = self.cfg("camera", "look_ahead", default=25)
        rider_position = self.cfg("camera", "rider_position", default=0.38)

        size = self.route_size()
        view_size = size * zoom_factor

        route_center_x = (min(self.xs) + max(self.xs)) / 2
        route_center_y = (min(self.ys) + max(self.ys)) / 2

        cx = self.xs[0]
        cy = self.ys[0]

        camera_frames = []

        for i in range(frames):
            index = max(1, int(len(self.xs) * (i + 1) / frames) - 1)
            index = min(index, len(self.xs) - 1)

            if mode == "fixed":
                center_x = route_center_x
                center_y = route_center_y

            elif mode == "follow":
                target_x = self.xs[index]
                target_y = self.ys[index]

                cx = cx * smoothness + target_x * (1 - smoothness)
                cy = cy * smoothness + target_y * (1 - smoothness)

                center_x = cx
                center_y = cy

            else:
                future_index = min(index + look_ahead, len(self.xs) - 1)

                rider_x = self.xs[index]
                rider_y = self.ys[index]

                future_x = self.xs[future_index]
                future_y = self.ys[future_index]

                # La caméra regarde un peu devant le cycliste
                target_x = rider_x * rider_position + future_x * (1 - rider_position)
                target_y = rider_y * rider_position + future_y * (1 - rider_position)

                cx = cx * smoothness + target_x * (1 - smoothness)
                cy = cy * smoothness + target_y * (1 - smoothness)

                center_x = cx
                center_y = cy

            camera_frames.append({
                "frame": i,
                "point_index": index,
                "center_x": center_x,
                "center_y": center_y,
                "view_size": view_size,
                "xlim": (center_x - view_size, center_x + view_size),
                "ylim": (center_y - view_size * 0.5625, center_y + view_size * 0.5625),
            })

        return camera_frames