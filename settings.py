from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

from paths import app_dir


SETTINGS_FILE = app_dir() / "user_settings.json"

_defaults: dict[str, Any] = {}


def _read_raw() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[settings] read {SETTINGS_FILE}: {e}")
        return {}


def _write_raw(data: dict[str, Any]) -> None:
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def _json_default(obj: Any) -> Any:
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"non-serializable: {type(obj)}")


def _coerce(value: Any, current: Any) -> Any:
    # JSON теряет tuple -> list; возвращаем tuple если в config он tuple.
    if isinstance(current, tuple) and isinstance(value, list):
        return tuple(_coerce(v, c) for v, c in zip(value, current)) \
            if len(value) == len(current) else tuple(value)
    if isinstance(current, dict) and isinstance(value, dict):
        return {k: _coerce(v, current.get(k, v)) for k, v in value.items()}
    return value


def load_into_config(config_module) -> None:
    data = _read_raw()
    for key, value in data.items():
        if not hasattr(config_module, key):
            continue
        current = getattr(config_module, key)
        try:
            setattr(config_module, key, _coerce(value, current))
        except Exception as e:
            print(f"[settings] apply {key}={value}: {e}")


def save(updates: dict[str, Any]) -> None:
    data = _read_raw()
    data.update(updates)
    _write_raw(data)


def save_one(key: str, value: Any) -> None:
    save({key: value})


def save_keys_from_config(config_module, keys: Iterable[str]) -> None:
    updates = {k: getattr(config_module, k) for k in keys if hasattr(config_module, k)}
    save(updates)


def snapshot_defaults(config_module) -> None:
    global _defaults
    _defaults = {
        k: copy.deepcopy(getattr(config_module, k))
        for k in dir(config_module)
        if not k.startswith("_") and k.isupper()
    }


def get_default(key: str) -> Any:
    return copy.deepcopy(_defaults.get(key))


def reset_keys(config_module, keys: Iterable[str]) -> None:
    data = _read_raw()
    for k in keys:
        if k in _defaults:
            setattr(config_module, k, copy.deepcopy(_defaults[k]))
        if k in data:
            del data[k]
    _write_raw(data)


def reset_all(config_module) -> None:
    for k, v in _defaults.items():
        setattr(config_module, k, copy.deepcopy(v))
    if SETTINGS_FILE.exists():
        SETTINGS_FILE.unlink()
