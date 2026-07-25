import numpy as np

from studio.geometry.resampler import PathResampler

pts = np.array([
    [0, 0, 100],
    [10, 0, 110],
    [20, 10, 120],
])

resampled = PathResampler(pts).resample(spacing=2)

print("Avant :", len(pts))
print("Après :", len(resampled))
print(resampled[:5])