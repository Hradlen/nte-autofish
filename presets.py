PRESETS: dict[str, dict] = {
    "1920×1080 (по умолчанию)": {
        "SELL_TAB_STORAGE":     (149, 414),
        "SELL_QUICK_BUTTON":    (1063, 964),
        "SELL_CONFIRM":         (1166, 706),
        "BUY_BAIT_PLUS":        (1775, 954),
        "BUY_BAIT_CONFIRM":     (1607, 1032),
        "BUY_PURCHASE_CONFIRM": (1166, 706),
        "BAIT_SELECT_CONFIRM":  (1157, 712),
        "CATCH_CLICK":          (761, 292),
        "ROI_BAR":              {"left": 593, "top": 41, "width": 747, "height": 61},
        "SHOP_GRID_ROI":        {"left": 37, "top": 151, "width": 640, "height": 695},
        "SHOP_GRID_COLS":       3,
        "SHOP_GRID_ROWS":       3,
        "BAIT_MATCH_THRESHOLD": 0.7,
    },

    "2560×1440 (2К)": {
        "SELL_TAB_STORAGE":     (193, 541),
        "SELL_QUICK_BUTTON":    (1412, 1286),
        "SELL_CONFIRM":         (1566, 945),
        "BUY_BAIT_PLUS":        (2363, 1266),
        "BUY_BAIT_CONFIRM":     (2157, 1365),
        "BUY_PURCHASE_CONFIRM": (1166, 706),
        "BAIT_SELECT_CONFIRM":  (1569, 948),
        "CATCH_CLICK":          (761, 292),
        "ROI_BAR":              {"left": 804, "top": 84, "width": 958, "height": 29},
        "SHOP_GRID_ROI":        {"left": 67, "top": 173, "width": 816, "height": 948},
        "SHOP_GRID_COLS":       3,
        "SHOP_GRID_ROWS":       3,
        "BAIT_MATCH_THRESHOLD": 0.7,
    },
}


def names() -> list[str]:
    return list(PRESETS.keys())


def get(name: str) -> dict:
    return PRESETS.get(name, {})
