import matplotlib.pyplot as plt
class Overlay:
    def __init__(self, config):
        self.config = config

    def title(self):
        return self.config.get("overlay", "title", default="GPX FLYOVER")

    def draw(self, ax, data):
        ax.text(
            0.03, 0.94,
            self.title(),
            transform=ax.transAxes,
            color="white",
            fontsize=24,
            fontweight="bold",
            bbox=dict(facecolor="black", alpha=0.70, edgecolor="none"),
        )

        lines = [
            f"Distance : {data['distance_km']:.2f} km",
            f"Progression : {data['progress'] * 100:.0f} %",
            f"Altitude : {data['altitude']:.0f} m",
            f"Vitesse : {data['speed_kmh']:.1f} km/h",
            f"Temps : {data['elapsed']}",
        ]

        y = 0.86
        for line in lines:
            ax.text(
                0.03, y,
                line,
                transform=ax.transAxes,
                color="white",
                fontsize=15,
                bbox=dict(facecolor="black", alpha=0.55, edgecolor="none"),
            )
            y -= 0.055

        # Barre de progression
        ax.add_patch(
            plt.Rectangle(
                (0.03, 0.04),
                0.50,
                0.018,
                transform=ax.transAxes,
                color="black",
                alpha=0.55,
            )
        )

        ax.add_patch(
            plt.Rectangle(
                (0.03, 0.04),
                0.50 * data["progress"],
                0.018,
                transform=ax.transAxes,
                color="#FC4C02",
                alpha=0.95,
            )
        )