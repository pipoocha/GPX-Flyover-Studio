from pathlib import Path

from PIL import Image


class MosaicBuilder:
    def __init__(self, tiles, provider="esri", zoom=15, cache_dir="cache/tiles"):
        self.tiles = tiles
        self.provider = provider
        self.zoom = zoom
        self.cache_dir = Path(cache_dir)

    def tile_path(self, tile):
        return (
            self.cache_dir
            / self.provider
            / str(tile.z)
            / str(tile.x)
            / f"{tile.y}.jpg"
        )

    def build(self, output_file="cache/tiles/mosaic.jpg"):
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        xs = [t.x for t in self.tiles]
        ys = [t.y for t in self.tiles]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        tile_size = 256

        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size

        mosaic = Image.new("RGB", (width, height))

        for tile in self.tiles:
            path = self.tile_path(tile)

            if not path.exists():
                continue

            img = Image.open(path).convert("RGB")

            px = (tile.x - min_x) * tile_size
            py = (tile.y - min_y) * tile_size

            mosaic.paste(img, (px, py))

        mosaic.save(output_file, quality=95)

        print("Mosaïque créée :")
        print(output_file.resolve())
        print("Taille :", width, "x", height)

        return output_file