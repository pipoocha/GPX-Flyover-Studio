from pathlib import Path


class DEMCache:

    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def list(self):
        return sorted(self.folder.glob("*.tif"))

    def exists(self, filename):
        return (self.folder / filename).exists()

    def path(self, filename):
        return self.folder / filename