from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import mss

import config
from paths import app_dir


_TEMPLATE_PATH = app_dir() / config.BAIT_TEMPLATE_PATH
_template_cache: Optional[np.ndarray] = None
_template_loaded = False


def template_exists() -> bool:
    return _TEMPLATE_PATH.exists()


def invalidate_template_cache() -> None:
    global _template_cache, _template_loaded
    _template_cache = None
    _template_loaded = False


def _load_template() -> Optional[np.ndarray]:
    global _template_cache, _template_loaded
    if _template_loaded:
        return _template_cache
    _template_loaded = True

    if not _TEMPLATE_PATH.exists():
        return None

    img = cv2.imread(str(_TEMPLATE_PATH), cv2.IMREAD_COLOR)
    if img is None:
        print(f"[shop_detect] не смог прочитать {_TEMPLATE_PATH}")
        return None

    _template_cache = img
    return img


def _grab(roi: dict) -> np.ndarray:
    sct = mss.mss()
    raw = np.array(sct.grab(roi))
    return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)


def _grid_roi() -> dict:
    return dict(config.SHOP_GRID_ROI)


def find_bait_tile(debug: bool = True) -> Optional[tuple[int, int]]:
    template = _load_template()
    if template is None:
        return None

    roi = _grid_roi()
    grid_img = _grab(roi)

    th_h, th_w = template.shape[:2]
    if th_h > grid_img.shape[0] or th_w > grid_img.shape[1]:
        print(
            f"[shop_detect] шаблон ({th_w}x{th_h}) больше grid ROI "
            f"({grid_img.shape[1]}x{grid_img.shape[0]})"
        )
        return None

    scales = [0.7, 0.85, 1.0, 1.15, 1.33, 1.5, 1.75, 2.0]
    orig_h, orig_w = template.shape[:2]
    max_val = -1.0
    max_loc = (0, 0)
    best_scale = 1.0
    best_w, best_h = orig_w, orig_h
    for s in scales:
        new_w = max(8, int(orig_w * s))
        new_h = max(8, int(orig_h * s))
        if new_w >= grid_img.shape[1] or new_h >= grid_img.shape[0]:
            continue
        scaled = cv2.resize(template, (new_w, new_h),
                            interpolation=cv2.INTER_CUBIC if s > 1.0 else cv2.INTER_AREA)
        r = cv2.matchTemplate(grid_img, scaled, cv2.TM_CCOEFF_NORMED)
        _, mv, _, ml = cv2.minMaxLoc(r)
        if debug:
            print(f"[shop_detect] scale {s:.2f} ({new_w}x{new_h}): {mv:.3f}")
        if mv > max_val:
            max_val = mv
            max_loc = ml
            best_scale = s
            best_w, best_h = new_w, new_h
    th_w, th_h = best_w, best_h
    if debug:
        print(f"[shop_detect] best: scale={best_scale:.2f} score={max_val:.3f} at {max_loc}")

    if max_val < config.BAIT_MATCH_THRESHOLD:
        print(
            f"[shop_detect] match {max_val:.2f} < threshold "
            f"{config.BAIT_MATCH_THRESHOLD}"
        )
        try:
            import time as _t
            dump_path = f"shop_grid_fail_{int(_t.time())}.png"
            cv2.imwrite(dump_path, grid_img)
            print(f"[shop_detect] grid dump -> {dump_path}")
        except Exception:
            pass
        return None

    match_cx = max_loc[0] + th_w // 2
    match_cy = max_loc[1] + th_h // 2

    cols = config.SHOP_GRID_COLS
    rows = config.SHOP_GRID_ROWS
    tile_w = roi["width"] / cols
    tile_h = roi["height"] / rows

    col = int(max(0, min(cols - 1, match_cx // tile_w)))
    row = int(max(0, min(rows - 1, match_cy // tile_h)))

    abs_x = int(roi["left"] + tile_w * (col + 0.5))
    abs_y = int(roi["top"] + tile_h * (row + 0.5))
    print(
        f"[shop_detect] tile: col={col} row={row} "
        f"score={max_val:.2f} -> ({abs_x},{abs_y})"
    )
    return (abs_x, abs_y)


def save_grid_dump(prefix: str = "shop_grid") -> str:
    roi = _grid_roi()
    img = _grab(roi)
    path = f"{prefix}.png"
    cv2.imwrite(path, img)
    print(f"  saved {path} ({img.shape[1]}x{img.shape[0]})")
    return path
