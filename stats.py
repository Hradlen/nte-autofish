from __future__ import annotations

import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

from paths import app_dir


STATS_FILE = app_dir() / "stats.jsonl"


class Stats:
    def __init__(self) -> None:
        self.session_start = time.time()
        self.casts = 0
        self.catches = 0
        self.misses = 0
        self.recent_cycles: deque = deque(maxlen=50)

        self._cycle_start: Optional[float] = None
        self._reaction_start: Optional[float] = None
        self._reaction_ms: Optional[float] = None
        self._minigame_start: Optional[float] = None

    def begin_cycle(self) -> None:
        self._cycle_start = time.time()
        self._reaction_start = None
        self._reaction_ms = None
        self._minigame_start = None
        self.casts += 1

    def mark_bite_visible(self) -> None:
        self._reaction_start = time.time()

    def mark_strike(self) -> None:
        if self._reaction_start is not None:
            self._reaction_ms = (time.time() - self._reaction_start) * 1000

    def mark_minigame(self) -> None:
        self._minigame_start = time.time()

    def end_cycle(self, caught: bool, reason: str = "") -> None:
        if self._cycle_start is None:
            return
        now = time.time()
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "duration_s": round(now - self._cycle_start, 2),
            "minigame_s": round(now - self._minigame_start, 2) if self._minigame_start else None,
            "reaction_ms": round(self._reaction_ms, 0) if self._reaction_ms else None,
            "caught": caught,
            "reason": reason or ("ok" if caught else "miss"),
        }
        self.recent_cycles.append(record)
        if caught:
            self.catches += 1
        else:
            self.misses += 1

        try:
            with STATS_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

        self._cycle_start = None
        self._reaction_start = None
        self._minigame_start = None

    def session_minutes(self) -> float:
        return (time.time() - self.session_start) / 60

    def fish_per_hour(self) -> float:
        h = self.session_minutes() / 60
        if h < 0.02:
            return 0.0
        return self.catches / h

    def success_rate(self) -> float:
        total = self.casts
        if total == 0:
            return 0.0
        return self.catches / total

    def avg_reaction_ms(self) -> Optional[float]:
        reactions = [c["reaction_ms"] for c in self.recent_cycles if c["reaction_ms"] is not None]
        if not reactions:
            return None
        return sum(reactions) / len(reactions)

    def avg_minigame_s(self) -> Optional[float]:
        durations = [c["minigame_s"] for c in self.recent_cycles if c["minigame_s"] is not None]
        if not durations:
            return None
        return sum(durations) / len(durations)

    def short_summary(self) -> str:
        return f"{self.catches} рыб {self.fish_per_hour():.1f}/ч {self.success_rate()*100:.0f}%"


def lifetime_total_catches() -> int:
    if not STATS_FILE.exists():
        return 0
    count = 0
    try:
        with STATS_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("caught"):
                    count += 1
    except Exception:
        pass
    return count


def lifetime_total_casts() -> int:
    if not STATS_FILE.exists():
        return 0
    count = 0
    try:
        with STATS_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
    except Exception:
        pass
    return count
