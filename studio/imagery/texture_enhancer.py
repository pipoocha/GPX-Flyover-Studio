from __future__ import annotations

from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageFilter


class TextureEnhancer:
    """Prépare une mosaïque satellite plus homogène pour le rendu vidéo.

    Le traitement reste volontairement doux : il ne floute pas le détail de
    l'image. Il corrige surtout les ruptures de luminosité à grande échelle et
    adoucit les coutures détectées entre blocs de la mosaïque.
    """

    def __init__(self, image_file: Path, metadata_file: Path | None = None):
        self.image_file = Path(image_file)
        self.metadata_file = Path(metadata_file) if metadata_file else None

    @property
    def output_file(self) -> Path:
        return self.image_file.with_name(self.image_file.stem + "_enhanced.png")

    def _signature(self) -> dict:
        stat = self.image_file.stat()
        return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "v": 4}

    @property
    def signature_file(self) -> Path:
        return self.output_file.with_suffix(".enhanced.json")

    def _is_current(self) -> bool:
        if not self.output_file.exists() or not self.signature_file.exists():
            return False
        try:
            return json.loads(self.signature_file.read_text(encoding="utf-8")) == self._signature()
        except Exception:
            return False

    @staticmethod
    def _smooth_illumination(rgb: np.ndarray) -> np.ndarray:
        """Réduit les grands rectangles d'exposition sans perdre les détails."""
        h, w, _ = rgb.shape
        # Carte de luminance très basse résolution : le rayon agit à l'échelle
        # de centaines de pixels, jamais sur les rochers/sentiers.
        small_w = max(24, min(96, w // 32))
        small_h = max(24, min(96, h // 32))
        lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])
        lum_img = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8))
        low = lum_img.resize((small_w, small_h), Image.Resampling.BILINEAR)
        low = low.filter(ImageFilter.GaussianBlur(radius=2.2))
        low = low.resize((w, h), Image.Resampling.BICUBIC)
        field = np.asarray(low, dtype=np.float32)

        target = float(np.median(field))
        # Correction limitée : préserve l'aspect naturel et les ombres réelles.
        gain = np.clip(target / np.maximum(field, 18.0), 0.82, 1.20)
        gain = 1.0 + (gain - 1.0) * 0.48
        return np.clip(rgb * gain[..., None], 0, 255)


    @staticmethod
    def _cinematic_tone(rgb: np.ndarray) -> np.ndarray:
        """Donne un rendu vidéo plus naturel à l'imagerie satellite.

        Les mosaïques brutes ont souvent des verts trop saturés et des ombres
        presque noires. Le traitement reste volontairement modéré pour ne pas
        fabriquer de détail artificiel.
        """
        rgb = np.clip(rgb, 0.0, 255.0).astype(np.float32)

        # Débouche les ombres sans blanchir les zones claires.
        lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])
        shadow = np.clip((92.0 - lum) / 92.0, 0.0, 1.0)
        lift = 28.0 * shadow * shadow
        rgb = rgb + lift[..., None]

        # Désaturation légère : les sources satellite sont souvent trop vives
        # une fois plaquées sur un relief éclairé en 3D.
        gray = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])[..., None]
        rgb = gray + (rgb - gray) * 0.76

        # Courbe douce de contraste, centrée sur les tons moyens.
        rgb = 128.0 + (rgb - 128.0) * 0.88

        # Balance aérienne très légère : évite le vert/bleu numérique sans
        # donner une dominante artificielle.
        rgb[..., 0] *= 1.015
        rgb[..., 1] *= 0.995
        rgb[..., 2] *= 0.985
        return np.clip(rgb, 0.0, 255.0)

    @staticmethod
    def _seam_scores(rgb: np.ndarray):
        # Travail sur une copie réduite pour détecter uniquement les coutures
        # longues et franches, pas les limites naturelles du paysage.
        h, w, _ = rgb.shape
        step = max(1, max(h, w) // 1800)
        sample = rgb[::step, ::step]
        gray = 0.2126 * sample[..., 0] + 0.7152 * sample[..., 1] + 0.0722 * sample[..., 2]
        dx = np.median(np.abs(gray[:, 1:] - gray[:, :-1]), axis=0)
        dy = np.median(np.abs(gray[1:, :] - gray[:-1, :]), axis=1)
        return dx, dy, step

    @staticmethod
    def _peaks(scores: np.ndarray, threshold: float, min_gap: int = 12):
        if scores.size == 0:
            return []
        baseline = float(np.median(scores))
        spread = float(np.median(np.abs(scores - baseline))) + 1e-6
        limit = max(threshold, baseline + 7.0 * spread)
        candidates = np.where(scores > limit)[0]
        if not len(candidates):
            return []
        peaks = []
        for idx in candidates:
            if not peaks or idx - peaks[-1] >= min_gap:
                peaks.append(int(idx))
            elif scores[idx] > scores[peaks[-1]]:
                peaks[-1] = int(idx)
        return peaks

    @staticmethod
    def _feather_vertical(rgb: np.ndarray, x: int, width: int):
        h, w, _ = rgb.shape
        if x <= width or x >= w - width:
            return
        left = rgb[:, x - width - 1].copy()
        right = rgb[:, x + width].copy()
        for k in range(-width, width + 1):
            t = (k + width) / max(1, 2 * width)
            rgb[:, x + k] = left * (1.0 - t) + right * t

    @staticmethod
    def _feather_horizontal(rgb: np.ndarray, y: int, width: int):
        h, w, _ = rgb.shape
        if y <= width or y >= h - width:
            return
        top = rgb[y - width - 1, :].copy()
        bottom = rgb[y + width, :].copy()
        for k in range(-width, width + 1):
            t = (k + width) / max(1, 2 * width)
            rgb[y + k, :] = top * (1.0 - t) + bottom * t

    def build(self, force: bool = False) -> Path:
        if not force and self._is_current():
            return self.output_file

        image = Image.open(self.image_file).convert("RGB")
        rgb = np.asarray(image, dtype=np.float32).copy()
        rgb = self._smooth_illumination(rgb)
        rgb = self._cinematic_tone(rgb)

        dx, dy, step = self._seam_scores(rgb)
        vertical = self._peaks(dx, threshold=8.0)
        horizontal = self._peaks(dy, threshold=8.0)
        feather = max(2, min(10, max(rgb.shape[:2]) // 1200))

        for p in vertical:
            self._feather_vertical(rgb, (p + 1) * step, feather)
        for p in horizontal:
            self._feather_horizontal(rgb, (p + 1) * step, feather)

        out = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
        out.save(self.output_file, format="PNG", optimize=False)
        self.signature_file.write_text(json.dumps(self._signature(), indent=2), encoding="utf-8")
        print(
            "Texture améliorée :",
            self.output_file,
            f"({len(vertical)} raccord(s) verticaux, {len(horizontal)} horizontal(aux))",
        )
        return self.output_file
