from studio.core.pipeline import FlyoverPipeline


class FlyoverApp:
    def __init__(self, project):
        self.project = project

    def run(self):
        FlyoverPipeline(self.project).run()
