import sys

from paths import app_dir


# При pythonw stdout/stderr могут быть None — пишем в app.log.
LOG_PATH = app_dir() / "app.log"
try:
    _log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None or not getattr(sys.stdout, "buffer", None):
        sys.stdout = _log_file
    if sys.stderr is None or not getattr(sys.stderr, "buffer", None):
        sys.stderr = _log_file
except Exception:
    pass

import config
import controller
import settings
import shop_detect


_HOTKEY_KEYS = (
    "HOTKEY_TOGGLE", "HOTKEY_QUIT", "HOTKEY_DEBUG",
    "HOTKEY_SELL", "HOTKEY_BUY_BAIT",
    "HOTKEY_TOGGLE_AUTO_SELL", "HOTKEY_TOGGLE_AUTO_BUY",
)


def _migrate_old_digit_hotkeys() -> None:
    data = settings._read_raw()
    changed = False
    for key in _HOTKEY_KEYS:
        v = data.get(key)
        if isinstance(v, str) and len(v) == 1 and v.isdigit():
            print(f"[migrate] {key}={v!r} -> drop")
            del data[key]
            changed = True
    if changed:
        settings._write_raw(data)


def _migrate_old_shop_grid() -> None:
    data = settings._read_raw()
    if "SHOP_GRID_FIRST_TILE_CENTER" not in data:
        return
    fx, fy = data.get("SHOP_GRID_FIRST_TILE_CENTER", (137, 258))
    sx = data.get("SHOP_GRID_TILE_STEP_X", 220)
    sy = data.get("SHOP_GRID_TILE_STEP_Y", 240)
    tw = data.get("SHOP_GRID_TILE_W", 200)
    th = data.get("SHOP_GRID_TILE_H", 215)
    cols = data.get("SHOP_GRID_COLS", 3)
    rows = data.get("SHOP_GRID_ROWS", 3)
    data["SHOP_GRID_ROI"] = {
        "left": int(fx - tw // 2),
        "top": int(fy - th // 2),
        "width": int((cols - 1) * sx + tw),
        "height": int((rows - 1) * sy + th),
    }
    for k in ("SHOP_GRID_FIRST_TILE_CENTER", "SHOP_GRID_TILE_STEP_X",
              "SHOP_GRID_TILE_STEP_Y", "SHOP_GRID_TILE_W", "SHOP_GRID_TILE_H"):
        data.pop(k, None)
    print(f"[migrate] свёрнуто в SHOP_GRID_ROI={data['SHOP_GRID_ROI']}")
    settings._write_raw(data)


def main() -> None:
    print("=" * 50)
    print("NTE Auto-Fish")
    print("=" * 50)

    if not controller.is_admin():
        print("[!] не от админа — нажатия не дойдут до игры от админа.")
        print("    Перезапусти start.bat от имени администратора.")
        print()

    settings.snapshot_defaults(config)
    _migrate_old_digit_hotkeys()
    _migrate_old_shop_grid()
    settings.load_into_config(config)

    if not shop_detect.template_exists():
        print(
            f"[!] Шаблон не найден: {config.BAIT_TEMPLATE_PATH}\n"
            f"    Авто-покупка упадёт. См. templates/README.txt."
        )
        print()

    print("Borderless / Windowed Fullscreen 1920x1080.")
    print(f"  {config.HOTKEY_TOGGLE.upper()} — старт/стоп")
    print(f"  {config.HOTKEY_SELL.upper()} — разовая продажа")
    print(f"  {config.HOTKEY_BUY_BAIT.upper()} — разовая закупка")
    print(f"  {config.HOTKEY_QUIT.upper()} — выход")
    print()

    from gui import App
    app = App()
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"Fatal: {e}\n{tb}")
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk(); r.withdraw()
            messagebox.showerror(
                "NTE Fish — фатальная ошибка",
                f"{e}\n\nПодробности в app.log",
            )
            r.destroy()
        except Exception:
            pass
        sys.exit(1)
