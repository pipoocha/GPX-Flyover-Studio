from studio.geometry.tube_builder import TubeBuilder


class Track:
    def __init__(self, path_coords, radius=8, sides=12):
        self.path_coords = path_coords
        self.radius = radius
        self.sides = sides

    def to_mesh(self):
        return TubeBuilder(
            self.path_coords,
            radius=self.radius,
            sides=self.sides,
        ).build()