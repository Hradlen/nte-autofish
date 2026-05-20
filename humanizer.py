import math
import random
import time

import config


def jitter(base: float, pct: float | None = None) -> float:
    if pct is None:
        pct = config.JITTER_PCT
    return base * random.uniform(1 - pct, 1 + pct)


def sleep_j(base: float, pct: float | None = None) -> None:
    time.sleep(jitter(base, pct))


def human_reaction() -> float:
    delay = random.uniform(config.HUMAN_REACTION_MIN, config.HUMAN_REACTION_MAX)
    time.sleep(delay)
    return delay


def click_jitter(x: int, y: int, radius: int | None = None) -> tuple[int, int]:
    if radius is None:
        radius = config.CLICK_JITTER_RADIUS
    angle = random.uniform(0, 2 * math.pi)
    r = random.uniform(0, radius)
    return int(x + r * math.cos(angle)), int(y + r * math.sin(angle))


def random_pause_between_cycles() -> None:
    time.sleep(random.uniform(config.INTER_CYCLE_PAUSE_MIN, config.INTER_CYCLE_PAUSE_MAX))


def should_long_pause() -> bool:
    return random.random() < config.LONG_PAUSE_PROBABILITY


def long_pause() -> None:
    time.sleep(random.uniform(config.LONG_PAUSE_MIN, config.LONG_PAUSE_MAX))


def should_intentional_miss() -> bool:
    return random.random() < config.MISS_PROBABILITY


class SessionLimiter:
    def __init__(self) -> None:
        self.session_start = time.time()
        self.break_until = 0.0
        self.in_break = False

    def should_pause(self) -> bool:
        now = time.time()

        if now < self.break_until:
            self.in_break = True
            return True

        if self.in_break:
            self.in_break = False
            self.session_start = now
            return False

        elapsed_min = (now - self.session_start) / 60
        if elapsed_min >= config.SESSION_MAX_MIN:
            duration_s = random.uniform(config.BREAK_MIN_MIN, config.BREAK_MAX_MIN) * 60
            self.break_until = now + duration_s
            return True

        return False

    def status(self) -> str:
        if self.in_break:
            remaining = max(0, self.break_until - time.time())
            return f"перерыв {remaining/60:.1f} мин"
        elapsed = (time.time() - self.session_start) / 60
        return f"сессия {elapsed:.1f}/{config.SESSION_MAX_MIN} мин"
