import cv2
import numpy as np

def overlay_ideal_on_real(
    real_bgr: np.ndarray,
    ideal_rgba: np.ndarray,
    center_px: tuple[int, int],
    alpha: float = 0.6
) -> np.ndarray:
    """
    Геометрично коректне накладання ideal (RGBA) на real (BGR)
    """

    h, w = real_bgr.shape[:2]
    ih, iw = ideal_rgba.shape[:2]

    cx, cy = center_px
    x0 = int(cx - iw / 2)
    y0 = int(cy - ih / 2)

    result = real_bgr.copy()

    for y in range(ih):
        for x in range(iw):
            ry = y0 + y
            rx = x0 + x

            if rx < 0 or ry < 0 or rx >= w or ry >= h:
                continue

            a = ideal_rgba[y, x, 3] / 255.0 * alpha
            if a <= 0:
                continue

            rgb = ideal_rgba[y, x, :3]

            result[ry, rx] = (
                (1 - a) * result[ry, rx] + a * rgb
            )

    return result.astype(np.uint8)
