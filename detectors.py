import cv2
import numpy as np
import mss

import config

_sct = mss.mss()


def grab(roi: dict) -> np.ndarray:
    raw = np.array(_sct.grab(roi))
    return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)


def _mask(img: np.ndarray, hsv_cfg: dict) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array(hsv_cfg["lower"]), np.array(hsv_cfg["upper"]))


def minigame_visible() -> bool:
    img = grab(config.ROI_BAR)
    mask = _mask(img, config.HSV_GREEN)
    return cv2.countNonZero(mask) > config.HSV_GREEN["min_pixels"]


def slider_offset() -> int | None:
    # >0 — ползунок правее центра (нажать A), <0 — левее (D), None — не нашли.
    img = grab(config.ROI_BAR)
    yellow = _mask(img, config.HSV_YELLOW)
    green = _mask(img, config.HSV_GREEN)

    ys = np.where(yellow.any(axis=0))[0]
    gs = np.where(green.any(axis=0))[0]
    if len(ys) == 0 or len(gs) == 0:
        return None

    return int(ys.mean()) - int(gs.mean())


def save_debug_dump(prefix: str = "debug") -> None:
    img = grab(config.ROI_BAR)
    path = f"{prefix}_bar.png"
    cv2.imwrite(path, img)
    print(f"  saved {path}")
