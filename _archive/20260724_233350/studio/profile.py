class ElevationProfile:
    def __init__(self, points, distances):
        self.points = points
        self.distances = distances
        self.elevations = [p["ele"] for p in points]

    def draw(self, ax, index):
        if len(self.points) < 2:
            return

        total_distance = max(self.distances[-1], 1)

        xs = [d / total_distance for d in self.distances]
        ys = self.elevations

        min_ele = min(ys)
        max_ele = max(ys)
        span = max(max_ele - min_ele, 1)

        # Zone profil en bas
        x0 = 0.08
        y0 = 0.08
        w = 0.84
        h = 0.13

        profile_x = [x0 + x * w for x in xs]
        profile_y = [y0 + ((e - min_ele) / span) * h for e in ys]

        # Profil complet
        ax.plot(
            profile_x,
            profile_y,
            transform=ax.transAxes,
            color="black",
            linewidth=5,
            alpha=0.55,
            zorder=30,
        )

        ax.plot(
            profile_x,
            profile_y,
            transform=ax.transAxes,
            color="#DDDDDD",
            linewidth=2,
            alpha=0.80,
            zorder=31,
        )

        # Profil parcouru
        ax.plot(
            profile_x[:index + 1],
            profile_y[:index + 1],
            transform=ax.transAxes,
            color="#FC4C02",
            linewidth=3,
            alpha=1.0,
            zorder=32,
        )

        # Curseur
        cursor_x = profile_x[index]
        cursor_y = profile_y[index]

        ax.scatter(
            cursor_x,
            cursor_y,
            transform=ax.transAxes,
            color="#FC4C02",
            s=70,
            zorder=33,
        )

        # Cadre discret
        ax.text(
            x0,
            y0 + h + 0.025,
            f"Profil altimétrique  {ys[index]:.0f} m",
            transform=ax.transAxes,
            color="white",
            fontsize=12,
            bbox=dict(facecolor="black", alpha=0.50, edgecolor="none"),
            zorder=34,
        )