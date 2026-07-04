import numpy as np

from studio.geometry.resampler import PathResampler
from studio.geometry.smoothing import ChaikinSmoother

pts = np.array([
    [0, 0, 0],
    [10, 0, 0],
    [20, 10, 0],
    [30, 10, 0],
])

resampled = PathResampler(pts).resample(spacing=2)
smooth = ChaikinSmoother(resampled).smooth(iterations=3)

print("Points origine :", len(pts))
print("Rééchantillonnés :", len(resampled))
print("Lissés :", len(smooth))
print(smooth[:10])