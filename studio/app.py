from studio.core.pipeline import FlyoverPipeline
from studio.core.project import FlyoverProject


class FlyoverApp:
    def __init__(self, gpx_file):
        self.gpx_file = gpx_file

    def run(self):
        project = FlyoverProject(gpx_file=self.gpx_file)
        pipeline = FlyoverPipeline(project)
        pipeline.run()