# Живая диагностика HSV-детекторов. Ctrl+C — выход.

from __future__ import annotations

import time

import cv2
import numpy as np

import config
import detectors


def _count_mask(img, hsv_cfg) -> int:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, np.array(hsv_cfg["lower"]), np.array(hsv_cfg["upper"]))
    return int(cv2.countNonZero(m))


def main() -> None:
    print("Live diagnostic. Ctrl+C — стоп.")
    print(f"Разрешение: {config.SCREEN_W}x{config.SCREEN_H}")
    print()
    print(f"{'green':>7} {'yellow':>7}  | флаги")
    print("-" * 40)

    while True:
        try:
            bar_img = detectors.grab(config.ROI_BAR)

            green = _count_mask(bar_img, config.HSV_GREEN)
            yellow = _count_mask(bar_img, config.HSV_YELLOW)

            flag_mg = "MG" if detectors.minigame_visible() else "  "

            print(f"{green:>7d} {yellow:>7d}  | {flag_mg}")
            time.sleep(0.3)
        except KeyboardInterrupt:
            print("\nstopped")
            break
        except Exception as e:
            print(f"error: {e}")
            time.sleep(0.5)


if __name__ == "__main__":
    main()
