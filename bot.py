from __future__ import annotations

import random
import time
from enum import Enum, auto
from typing import Optional

import config
import controller
import detectors
import humanizer as humanize
import shop_detect
from stats import Stats


class State(Enum):
    IDLE = auto()
    WAITING_BITE = auto()
    MINIGAME = auto()
    CAUGHT = auto()
    BREAK = auto()
    SELLING = auto()
    BUYING_BAIT = auto()


class FishingBot:
    def __init__(self) -> None:
        self.state = State.IDLE
        self.last_action_ts = 0.0
        self.minigame_lost_ts: Optional[float] = None
        self.fish_count = 0
        self.last_action: str = "-"
        self.session = humanize.SessionLimiter() if config.HUMANIZE else None
        self.stats = Stats()
        self._intentional_miss = False
        self._held_key: Optional[str] = None
        self._release_target: float = 0.0
        self._sell_requested = False
        self._buy_bait_requested = False
        self._stop_after_chain = False
        self._should_stop = False
        self._casts_remaining = config.INITIAL_BAIT_BUDGET
        self._minigame_was_seen = False
        self._cooldown_until = 0.0
        self._strike_attempts = 0
        self._next_strike_ts = 0.0
        self._first_strike_at = 0.0

        self._state_entered_ts = time.time()
        self._last_state_seen = self.state

    def request_sell(self) -> None:
        if self._sell_requested:
            return
        self._sell_requested = True
        self.log("автопродажа запрошена")

    def request_buy_bait(self) -> None:
        if self._buy_bait_requested:
            return
        self._buy_bait_requested = True
        self.log("автопокупка запрошена")

    def toggle_auto_sell(self) -> bool:
        config.AUTO_SELL_ENABLED = not config.AUTO_SELL_ENABLED
        self.log(f"авто-продажа: {'ВКЛ' if config.AUTO_SELL_ENABLED else 'ВЫКЛ'}")
        return config.AUTO_SELL_ENABLED

    def toggle_auto_buy(self) -> bool:
        config.AUTO_BUY_ENABLED = not config.AUTO_BUY_ENABLED
        self.log(f"авто-закупка: {'ВКЛ' if config.AUTO_BUY_ENABLED else 'ВЫКЛ'}")
        return config.AUTO_BUY_ENABLED

    def _play_alert(self) -> None:
        try:
            import winsound
            for freq, dur in [(880, 200), (660, 200), (880, 200), (660, 400)]:
                winsound.Beep(freq, dur)
        except Exception:
            pass

    def log(self, msg: str) -> None:
        print(f"[{self.state.name}] {msg}")
        self.last_action = msg

    def _hold_key(self, key: str) -> None:
        if self._held_key == key:
            return
        if self._held_key is not None:
            controller.key_up(self._held_key)
        controller.key_down(key)
        self._held_key = key

    def _release_held_key(self) -> None:
        if self._held_key is not None:
            controller.key_up(self._held_key)
            self._held_key = None

    def cleanup(self) -> None:
        self._release_held_key()

    def _check_watchdog(self) -> bool:
        now = time.time()
        if self.state != self._last_state_seen:
            self._last_state_seen = self.state
            self._state_entered_ts = now
            return False

        timeout = config.WATCHDOG_TIMEOUT.get(self.state.name, 90)
        elapsed = now - self._state_entered_ts
        if elapsed <= timeout:
            return False

        self.log(f"WATCHDOG: stuck in {self.state.name} for {elapsed:.0f}s, esc reset")
        self._release_held_key()

        try:
            controller.tap("esc")
            time.sleep(0.4)
            controller.tap("esc")
            time.sleep(0.6)
        except Exception:
            pass

        if self.stats._cycle_start is not None:
            self.stats.end_cycle(caught=False, reason="watchdog")

        self.state = State.IDLE
        self._state_entered_ts = time.time()
        self._last_state_seen = self.state
        return True

    def _sleep(self, base: float) -> None:
        if config.HUMANIZE:
            humanize.sleep_j(base)
        else:
            time.sleep(base)

    def _handle_idle(self) -> None:
        if self._sell_requested:
            self._sell_requested = False
            self.state = State.SELLING
            return

        if self._buy_bait_requested:
            self._buy_bait_requested = False
            self.state = State.BUYING_BAIT
            return

        if self._stop_after_chain:
            self._stop_after_chain = False
            self.log("цепочка sell/buy завершена — СТОП")
            self._play_alert()
            self._should_stop = True
            return

        if self._casts_remaining <= 0:
            self._trigger_auto_buy_cycle()
            return

        if self.session and self.session.should_pause():
            self.log(f"перерыв ({self.session.status()})")
            self.state = State.BREAK
            return

        if config.HUMANIZE:
            humanize.random_pause_between_cycles()
            if humanize.should_long_pause():
                self.log("длинная пауза")
                humanize.long_pause()
            self._intentional_miss = humanize.should_intentional_miss()

        controller.tap("f")

        cast_delay = humanize.jitter(config.CAST_DELAY) if config.HUMANIZE else config.CAST_DELAY
        time.sleep(cast_delay)

        self._casts_remaining -= 1
        self.stats.begin_cycle()
        suffix = " (miss)" if self._intentional_miss else ""
        self.log(f"заброс{suffix} | наживки осталось: {self._casts_remaining}")
        self.state = State.WAITING_BITE
        self.last_action_ts = time.time()
        self._strike_attempts = 0
        self._next_strike_ts = 0.0
        self._minigame_was_seen = False
        wait_offset = (
            humanize.jitter(config.MIN_BITE_WAIT) if config.HUMANIZE
            else config.MIN_BITE_WAIT
        )
        self._first_strike_at = time.time() + wait_offset

    def _trigger_auto_buy_cycle(self) -> None:
        self.log("наживка кончилась — авто-цикл")

        sell = config.AUTO_SELL_ENABLED
        buy = config.AUTO_BUY_ENABLED

        self._sell_requested = sell
        self._buy_bait_requested = buy

        if not buy:
            self._stop_after_chain = True
            actions = ["sell"] if sell else []
            actions.append("STOP")
            self.log(f"авто-цикл: {' -> '.join(actions)}")
        else:
            actions = ["sell"] if sell else []
            actions.append("buy")
            self.log(f"авто-цикл: {' -> '.join(actions)}")

    def _handle_waiting_bite(self) -> None:
        if time.time() < self._first_strike_at:
            return

        if time.time() < self._cooldown_until:
            self.last_action = f"кулдаун {self._cooldown_until - time.time():.1f}с"
            return

        if detectors.minigame_visible():
            self.stats.mark_strike()
            self.stats.mark_minigame()
            self.log(f"подсечка ок (попытка {max(self._strike_attempts, 1)})")
            self.state = State.MINIGAME
            self.last_action_ts = time.time()
            self.minigame_lost_ts = None
            self._minigame_was_seen = True
            return

        def _next_interval() -> float:
            return (
                humanize.jitter(config.STRIKE_INTERVAL) if config.HUMANIZE
                else config.STRIKE_INTERVAL
            )

        if self._strike_attempts == 0:
            controller.tap("f")
            self._strike_attempts = 1
            self._next_strike_ts = time.time() + _next_interval()
            self.last_action = f"попытка 1/{config.STRIKE_MAX_ATTEMPTS}"
            return

        if time.time() < self._next_strike_ts:
            self.last_action = (
                f"попытка {self._strike_attempts}/{config.STRIKE_MAX_ATTEMPTS} "
                f"(жду {self._next_strike_ts - time.time():.1f}с)"
            )
            return

        if self._strike_attempts >= config.STRIKE_MAX_ATTEMPTS:
            self.log(f"подсечка не удалась ({config.STRIKE_MAX_ATTEMPTS} попыток), перезаход")
            self.stats.end_cycle(caught=False, reason="strike_exhausted")
            self.state = State.IDLE
            return

        self._strike_attempts += 1
        self._next_strike_ts = time.time() + _next_interval()
        controller.tap("f")
        self.last_action = f"попытка {self._strike_attempts}/{config.STRIKE_MAX_ATTEMPTS}"

    def _handle_minigame(self) -> None:
        visible = detectors.minigame_visible()

        if not visible:
            self._release_held_key()

            if not self._minigame_was_seen:
                elapsed_since_strike = time.time() - self.last_action_ts
                if elapsed_since_strike < config.MINIGAME_APPEAR_TIMEOUT:
                    self.last_action = f"жду полосу ({elapsed_since_strike:.1f}с)"
                    return
                self.log(f"полоса не появилась за {elapsed_since_strike:.1f}с — ложная подсечка")
                self.stats.end_cycle(caught=False, reason="false_strike")
                self.state = State.IDLE
                return

            if self.minigame_lost_ts is None:
                self.minigame_lost_ts = time.time()
            elif time.time() - self.minigame_lost_ts > config.MINIGAME_END_GRACE:
                self.state = State.CAUGHT
            return

        self._minigame_was_seen = True
        self.minigame_lost_ts = None
        offset = detectors.slider_offset()
        if offset is None:
            return

        trigger = config.HOLD_TRIGGER_PX
        if config.HUMANIZE:
            trigger = humanize.jitter(trigger, 0.15)

        if self._held_key is None:
            if offset > trigger:
                self._release_target = random.uniform(-config.RELEASE_BIAS_PX, config.RELEASE_BIAS_PX)
                self._hold_key("a")
                self.last_action = f"hold A ({offset:+d} -> {self._release_target:+.0f})"
            elif offset < -trigger:
                self._release_target = random.uniform(-config.RELEASE_BIAS_PX, config.RELEASE_BIAS_PX)
                self._hold_key("d")
                self.last_action = f"hold D ({offset:+d} -> {self._release_target:+.0f})"
            else:
                self.last_action = f"drift {offset:+d}"

        elif self._held_key == "a":
            if offset <= self._release_target:
                self._release_held_key()
                self.last_action = f"release A at {offset:+d}"
            else:
                self.last_action = f"hold A {offset:+d} -> {self._release_target:+.0f}"

        elif self._held_key == "d":
            if offset >= self._release_target:
                self._release_held_key()
                self.last_action = f"release D at {offset:+d}"
            else:
                self.last_action = f"hold D {offset:+d} -> {self._release_target:+.0f}"

    def _handle_caught(self) -> None:
        self.fish_count += 1
        self.stats.end_cycle(caught=True, reason="ok")
        status = self.session.status() if self.session else ""
        self.log(f"поймано. всего: {self.fish_count}. {status}")

        base_x, base_y = config.CATCH_CLICK
        for wait_s, radius in [(0.5, 50), (0.7, 90), (0.5, 40)]:
            time.sleep(wait_s)
            if config.HUMANIZE:
                cx, cy = humanize.click_jitter(base_x, base_y, radius)
            else:
                cx, cy = base_x, base_y
            controller.click(cx, cy)
            self.last_action = f"закрытие награды ({radius}px)"

        self._sleep(0.4)
        self._cooldown_until = time.time() + config.POST_CATCH_COOLDOWN
        self.state = State.IDLE

    def _handle_break(self) -> None:
        if not self.session or not self.session.should_pause():
            self.log("перерыв окончен")
            self.state = State.IDLE
            return
        self.last_action = self.session.status()
        time.sleep(2.0)

    def _handle_selling(self) -> None:
        def step(name: str, fn) -> None:
            self.last_action = f"sell: {name}"
            print(f"[SELLING] {name}")
            fn()

        def click_jit(coord, radius=15) -> None:
            if config.HUMANIZE:
                cx, cy = humanize.click_jitter(*coord, radius=radius)
            else:
                cx, cy = coord
            controller.click(cx, cy)

        def wait(base: float) -> None:
            time.sleep(humanize.jitter(base) if config.HUMANIZE else base)

        try:
            step("Q (меню)", lambda: controller.tap("q"))
            wait(config.SELL_OPEN_DELAY)

            step("вкладка Хранилище", lambda: click_jit(config.SELL_TAB_STORAGE))
            wait(config.SELL_TAB_DELAY)

            step("Быстрая продажа", lambda: click_jit(config.SELL_QUICK_BUTTON))
            wait(config.SELL_BUTTON_DELAY)

            step("Подтвердить", lambda: click_jit(config.SELL_CONFIRM, radius=20))
            wait(config.SELL_CONFIRM_DELAY)

            step("ESC #1", lambda: controller.tap("esc"))
            time.sleep(1.5)

            step("ESC #2", lambda: controller.tap("esc"))
            wait(config.SELL_CLOSE_DELAY)

            self.log("автопродажа ок")
        except Exception as e:
            self.log(f"автопродажа: {e}")
            try:
                controller.tap("esc")
                time.sleep(0.5)
                controller.tap("esc")
            except Exception:
                pass

        self.state = State.IDLE

    def _handle_buying_bait(self) -> None:
        def click_jit(coord, radius=15) -> None:
            if config.HUMANIZE:
                cx, cy = humanize.click_jitter(*coord, radius=radius)
            else:
                cx, cy = coord
            controller.click(cx, cy)

        def wait(base: float) -> None:
            time.sleep(humanize.jitter(base) if config.HUMANIZE else base)

        try:
            self.last_action = "buy: R (меню)"
            print("[BUYING_BAIT] R (меню)")
            controller.tap("r")
            wait(config.BUY_OPEN_DELAY)

            tile_pt = shop_detect.find_bait_tile()
            if tile_pt is None:
                if not shop_detect.template_exists():
                    raise RuntimeError(
                        "templates/bait_target.png не найден"
                    )
                raise RuntimeError("плитка наживки не найдена")

            self.last_action = f"buy: tile @ {tile_pt}"
            print(f"[BUYING_BAIT] tile {tile_pt}")
            click_jit(tile_pt)
            wait(config.BUY_SELECT_DELAY)

            plus_clicks = max(0, config.BUY_BAIT_COUNT - 1)
            print(f"[BUYING_BAIT] +{plus_clicks}")
            for i in range(plus_clicks):
                self.last_action = f"buy: + ({i + 1}/{plus_clicks})"
                click_jit(config.BUY_BAIT_PLUS, radius=6)
                interval = config.BUY_PLUS_INTERVAL
                if config.HUMANIZE:
                    interval = humanize.jitter(interval, 0.3)
                time.sleep(interval)

            self.last_action = "buy: Купить"
            print("[BUYING_BAIT] Купить")
            click_jit(config.BUY_BAIT_CONFIRM, radius=20)
            wait(config.BUY_PURCHASE_DELAY)

            if config.BUY_BAIT_COUNT >= config.BUY_CONFIRM_THRESHOLD:
                self.last_action = "buy: Подтвердить"
                print(f"[BUYING_BAIT] Подтвердить (>= {config.BUY_CONFIRM_THRESHOLD})")
                click_jit(config.BUY_PURCHASE_CONFIRM, radius=20)
            else:
                print(f"[BUYING_BAIT] skip подтверждение (< {config.BUY_CONFIRM_THRESHOLD})")

            time.sleep(2.5)

            self.last_action = "buy: ESC #1"
            print("[BUYING_BAIT] ESC #1")
            controller.tap("esc")
            time.sleep(1.5)

            self.last_action = "buy: ESC #2"
            print("[BUYING_BAIT] ESC #2")
            controller.tap("esc")
            wait(config.BUY_CLOSE_DELAY)

            self.last_action = "bait: E"
            print("[BUYING_BAIT] E (смена)")
            controller.tap("e")
            wait(config.BAIT_SELECT_OPEN_DELAY)

            self.last_action = "bait: Сменить"
            print("[BUYING_BAIT] Сменить")
            click_jit(config.BAIT_SELECT_CONFIRM, radius=20)
            wait(config.BAIT_SELECT_CONFIRM_DELAY)

            self._casts_remaining = config.BUY_BAIT_COUNT
            self.log(
                f"автопокупка x{config.BUY_BAIT_COUNT} ок "
                f"(счётчик: {self._casts_remaining})"
            )
        except Exception as e:
            self.log(f"автопокупка: {e}")
            try:
                controller.tap("esc")
                time.sleep(0.5)
                controller.tap("esc")
            except Exception:
                pass
            self._play_alert()
            self._should_stop = True

        self.state = State.IDLE

    def tick(self) -> None:
        if self._check_watchdog():
            return

        if self.state is State.IDLE:
            self._handle_idle()
        elif self.state is State.WAITING_BITE:
            self._handle_waiting_bite()
        elif self.state is State.MINIGAME:
            self._handle_minigame()
        elif self.state is State.CAUGHT:
            self._handle_caught()
        elif self.state is State.BREAK:
            self._handle_break()
        elif self.state is State.SELLING:
            self._handle_selling()
        elif self.state is State.BUYING_BAIT:
            self._handle_buying_bait()
