from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


class Terrain3D:
    def __init__(self, points, xs, ys, output_dir):
        self.points = points
        self.xs = np.array(xs)
        self.ys = np.array(ys)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_preview(self):
        elevations = np.array([p["ele"] for p in self.points])

        x = (self.xs - self.xs.mean()) / 1000
        y = (self.ys - self.ys.mean()) / 1000

        grid_size = 120
        gx = np.linspace(x.min() - 1, x.max() + 1, grid_size)
        gy = np.linspace(y.min() - 1, y.max() + 1, grid_size)
        X, Y = np.meshgrid(gx, gy)

        Z = np.zeros_like(X)

        step = max(1, len(x) // 250)

        for i in range(0, len(x), step):
            d = np.sqrt((X - x[i]) ** 2 + (Y - y[i]) ** 2)
            Z += elevations[i] / (d + 0.25)

        W = np.zeros_like(X)

        for i in range(0, len(x), step):
            d = np.sqrt((X - x[i]) ** 2 + (Y - y[i]) ** 2)
            W += 1 / (d + 0.25)

        Z = Z / W

        fig = plt.figure(figsize=(14, 9))
        ax = fig.add_subplot(111, projection="3d")

        ax.plot_surface(X, Y, Z, cmap="terrain", alpha=0.85, linewidth=0)

        ax.plot(
            x,
            y,
            elevations + 15,
            color="#FC4C02",
            linewidth=4
        )

        ax.set_title("GPX Flyover Studio - Aperçu 3D")
        ax.set_axis_off()
        ax.view_init(elev=55, azim=-60)

        output_file = self.output_dir / "terrain_3d_preview.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=150)
        plt.close(fig)

        print("Aperçu 3D créé :", output_file)