from __future__ import annotations

import ctypes
import sys
import threading
import time
import tkinter as tk
from typing import Any, Callable

import customtkinter as ctk
import keyboard

import config
import settings
from bot import FishingBot
from overlay import Overlay
from paths import resource_dir


_user32 = ctypes.windll.user32 if sys.platform == "win32" else None


def _example_image_for(config_key: str) -> str | None:
    p = resource_dir() / "templates" / "examples" / f"{config_key}.png"
    return str(p) if p.exists() else None


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


COLOR_OK = "#22c55e"
COLOR_BAD = "#ef4444"
COLOR_MUTED = "#888888"
COLOR_ACCENT = "#3b82f6"


# Linked-поля
# ============================================================

class LinkedField:
    def __init__(
        self,
        parent: ctk.CTkFrame,
        config_key: str,
        label: str,
        kind: str = "int",
        validator: Callable[[Any], bool] | None = None,
        width: int = 90,
        on_apply: Callable[[], None] | None = None,
    ):
        self.config_key = config_key
        self.kind = kind
        self.validator = validator
        self.on_apply = on_apply

        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(self.frame, text=label, anchor="w", width=300).pack(side="left")

        current = getattr(config, config_key)
        self.var = tk.StringVar(value=self._format(current))
        self.entry = ctk.CTkEntry(self.frame, textvariable=self.var, width=width)
        self.entry.pack(side="left", padx=(8, 8))

        self.indicator = ctk.CTkLabel(self.frame, text="", width=20, text_color=COLOR_OK)
        self.indicator.pack(side="left")

        self.entry.bind("<FocusOut>", self._on_change)
        self.entry.bind("<Return>", self._on_change)

    def pack(self, **kw):
        self.frame.pack(**kw)

    def _format(self, v: Any) -> str:
        return str(v)

    def _parse(self, raw: str) -> Any:
        if self.kind == "int":
            return int(raw)
        if self.kind == "float":
            return float(raw)
        return raw

    def _on_change(self, *_):
        ok, _ = self.validate()
        if ok:
            self._mark_ok()
        else:
            self._mark_bad()

    def validate(self) -> tuple[bool, str]:
        raw = self.var.get().strip()
        try:
            value = self._parse(raw)
        except (ValueError, TypeError):
            return False, f"{self.config_key}: не число"
        if self.validator and not self.validator(value):
            return False, f"{self.config_key}: вне диапазона"
        return True, ""

    def apply(self) -> None:
        raw = self.var.get().strip()
        value = self._parse(raw)
        setattr(config, self.config_key, value)
        settings.save_one(self.config_key, value)
        self._mark_ok()
        if self.on_apply:
            self.on_apply()

    def _mark_ok(self):
        self.indicator.configure(text="✓", text_color=COLOR_OK)

    def _mark_bad(self):
        self.indicator.configure(text="✗", text_color=COLOR_BAD)

    def refresh(self):
        self.var.set(self._format(getattr(config, self.config_key)))
        self.indicator.configure(text="")

    def set_value(self, value):
        self.var.set(self._format(value))
        self._mark_ok()


def _label_column(parent: ctk.CTkFrame, label: str, hint: str | None = None,
                  width: int = 320) -> ctk.CTkFrame:
    col = ctk.CTkFrame(parent, fg_color="transparent", width=width)
    col.pack_propagate(False)
    ctk.CTkLabel(col, text=label, anchor="w", justify="left").pack(anchor="w")
    if hint:
        ctk.CTkLabel(
            col, text=hint, anchor="w", justify="left",
            text_color=COLOR_MUTED, font=ctk.CTkFont(size=10),
        ).pack(anchor="w")
    return col


class LinkedPoint:
    def __init__(self, parent: ctk.CTkFrame, config_key: str, label: str,
                 hint: str | None = None):
        self.config_key = config_key
        self.label = label
        self.hint = hint
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        col = _label_column(self.frame, label, hint)
        col.configure(height=44 if hint else 28)
        col.pack(side="left")

        x, y = getattr(config, config_key)
        self.x_var = tk.StringVar(value=str(x))
        self.y_var = tk.StringVar(value=str(y))

        ctk.CTkLabel(self.frame, text="x", text_color=COLOR_MUTED, width=12).pack(side="left")
        ex = ctk.CTkEntry(self.frame, textvariable=self.x_var, width=60)
        ex.pack(side="left", padx=(2, 8))
        ctk.CTkLabel(self.frame, text="y", text_color=COLOR_MUTED, width=12).pack(side="left")
        ey = ctk.CTkEntry(self.frame, textvariable=self.y_var, width=60)
        ey.pack(side="left", padx=(2, 8))

        self.indicator = ctk.CTkLabel(self.frame, text="", width=20, text_color=COLOR_OK)
        self.indicator.pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            self.frame, text="Указать", width=110, height=28,
            corner_radius=8, fg_color="transparent", border_width=1,
            border_color=COLOR_MUTED, text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray25"),
            command=self._open_picker,
        ).pack(side="left")

        for w in (ex, ey):
            w.bind("<FocusOut>", self._on_change)
            w.bind("<Return>", self._on_change)

    def pack(self, **kw):
        self.frame.pack(**kw)

    def _on_change(self, *_):
        ok, _ = self.validate()
        if ok:
            self.indicator.configure(text="✓", text_color=COLOR_OK)
        else:
            self.indicator.configure(text="✗", text_color=COLOR_BAD)

    def validate(self) -> tuple[bool, str]:
        try:
            int(self.x_var.get().strip())
            int(self.y_var.get().strip())
        except ValueError:
            return False, f"{self.config_key}: x/y должны быть целыми"
        return True, ""

    def apply(self) -> None:
        x = int(self.x_var.get().strip())
        y = int(self.y_var.get().strip())
        value = (x, y)
        setattr(config, self.config_key, value)
        settings.save_one(self.config_key, value)
        self.indicator.configure(text="✓", text_color=COLOR_OK)

    def refresh(self):
        x, y = getattr(config, self.config_key)
        self.x_var.set(str(x))
        self.y_var.set(str(y))
        self.indicator.configure(text="")

    def set_value(self, value):
        x, y = value[0], value[1]
        self.x_var.set(str(x))
        self.y_var.set(str(y))
        self.indicator.configure(text="✓", text_color=COLOR_OK)

    def _open_picker(self):
        from picker import PointPicker
        PointPicker(
            parent=self.frame.winfo_toplevel(),
            title=f"Указать координату: {self.label}",
            on_done=self._on_pick_done,
            example_image_path=_example_image_for(self.config_key),
        )

    def _on_pick_done(self, value):
        if value is None:
            return
        x, y = value
        self.x_var.set(str(x))
        self.y_var.set(str(y))
        self.indicator.configure(text="✓", text_color=COLOR_OK)


class LinkedROI:
    def __init__(self, parent: ctk.CTkFrame, config_key: str, label: str,
                 hint: str | None = None):
        self.config_key = config_key
        self.label = label
        self.hint = hint
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        col = _label_column(self.frame, label, hint)
        col.configure(height=44 if hint else 28)
        col.pack(side="left")

        roi = getattr(config, config_key)
        self.vars: dict[str, tk.StringVar] = {}
        for key in ("left", "top", "width", "height"):
            self.vars[key] = tk.StringVar(value=str(roi[key]))
            ctk.CTkLabel(self.frame, text=key[0], text_color=COLOR_MUTED, width=12).pack(side="left")
            e = ctk.CTkEntry(self.frame, textvariable=self.vars[key], width=55)
            e.pack(side="left", padx=(2, 4))
            e.bind("<FocusOut>", self._on_change)
            e.bind("<Return>", self._on_change)

        self.indicator = ctk.CTkLabel(self.frame, text="", width=20, text_color=COLOR_OK)
        self.indicator.pack(side="left", padx=(4, 4))

        ctk.CTkButton(
            self.frame, text="Указать", width=110, height=28,
            corner_radius=8, fg_color="transparent", border_width=1,
            border_color=COLOR_MUTED, text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray25"),
            command=self._open_picker,
        ).pack(side="left")

    def pack(self, **kw):
        self.frame.pack(**kw)

    def _on_change(self, *_):
        ok, _ = self.validate()
        if ok:
            self.indicator.configure(text="✓", text_color=COLOR_OK)
        else:
            self.indicator.configure(text="✗", text_color=COLOR_BAD)

    def validate(self) -> tuple[bool, str]:
        try:
            roi = {k: int(v.get().strip()) for k, v in self.vars.items()}
        except ValueError:
            return False, f"{self.config_key}: нужны 4 целых числа"
        if roi["width"] <= 0 or roi["height"] <= 0:
            return False, f"{self.config_key}: width/height > 0"
        return True, ""

    def apply(self) -> None:
        roi = {k: int(v.get().strip()) for k, v in self.vars.items()}
        setattr(config, self.config_key, roi)
        settings.save_one(self.config_key, roi)
        self.indicator.configure(text="✓", text_color=COLOR_OK)

    def refresh(self):
        roi = getattr(config, self.config_key)
        for k, v in self.vars.items():
            v.set(str(roi[k]))
        self.indicator.configure(text="")

    def set_value(self, value):
        for k in ("left", "top", "width", "height"):
            if k in value:
                self.vars[k].set(str(value[k]))
        self.indicator.configure(text="✓", text_color=COLOR_OK)

    def _open_picker(self):
        from picker import RoiPicker
        RoiPicker(
            parent=self.frame.winfo_toplevel(),
            title=f"Указать область: {self.label}",
            on_done=self._on_pick_done,
            example_image_path=_example_image_for(self.config_key),
        )

    def _on_pick_done(self, value):
        if value is None:
            return
        for k in ("left", "top", "width", "height"):
            self.vars[k].set(str(value[k]))
        self.indicator.configure(text="✓", text_color=COLOR_OK)


class LinkedSwitch:
    def __init__(
        self,
        parent: ctk.CTkFrame,
        config_key: str,
        label: str,
        on_apply: Callable[[bool], None] | None = None,
    ):
        self.config_key = config_key
        self.on_apply = on_apply
        self.var = tk.BooleanVar(value=bool(getattr(config, config_key)))
        self.widget = ctk.CTkSwitch(
            parent, text=label, variable=self.var, command=self._on_change
        )

    def pack(self, **kw):
        self.widget.pack(**kw)

    def _on_change(self):
        if self.on_apply:
            self.on_apply(bool(self.var.get()))

    def validate(self) -> tuple[bool, str]:
        return True, ""

    def apply(self) -> None:
        v = bool(self.var.get())
        setattr(config, self.config_key, v)
        settings.save_one(self.config_key, v)

    def set(self, value: bool):
        self.var.set(value)
        self._on_change()

    def refresh(self):
        self.var.set(bool(getattr(config, self.config_key)))


class _TextStream:
    def __init__(self, textbox: ctk.CTkTextbox, original):
        self.tb = textbox
        self.original = original
        self._at_line_start = True

    def write(self, s: str):
        try:
            self.original.write(s)
            self.original.flush()
        except Exception:
            pass
        try:
            self.tb.after(0, self._append, s)
        except Exception:
            pass

    def _append(self, s: str):
        from datetime import datetime
        out: list[str] = []
        for ch in s:
            if self._at_line_start and ch != "\n":
                out.append(f"[{datetime.now().strftime('%H:%M:%S')}] ")
                self._at_line_start = False
            out.append(ch)
            if ch == "\n":
                self._at_line_start = True
        text = "".join(out)

        self.tb.configure(state="normal")
        self.tb.insert("end", text)
        self.tb.see("end")
        try:
            line_count = int(self.tb.index("end-1c").split(".")[0])
            if line_count > 2000:
                self.tb.delete("1.0", "1500.0")
        except Exception:
            pass
        self.tb.configure(state="disabled")

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass


class App:
    SIDEBAR_W = 200

    TABS = ("Главная", "Координаты", "Тайминги", "Хоткеи", "Статистика", "Логи")

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("NTE Auto-Fish")
        self.root.geometry("1000x680")
        self.root.minsize(900, 580)

        try:
            ico = resource_dir() / "icon.ico"
            if ico.exists():
                self.root.iconbitmap(default=str(ico))
        except Exception:
            pass

        self.bot: FishingBot | None = None
        self._running = False
        self._quit = False
        self._last_toggle_ts = 0.0
        self._current_tab = ""

        self._linked: dict[str, list] = {}
        self._capturing_for: str | None = None

        self.overlay: Overlay | None = None

        self._build_layout()
        self._build_tabs()
        self._show_tab("Главная")

        threading.Thread(target=self._hotkey_loop, daemon=True).start()
        threading.Thread(target=self._bot_loop, daemon=True).start()
        self.root.after(250, self._update_status)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self.root, width=self.SIDEBAR_W, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar, text="NTE Fish",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(
            self.sidebar, text="auto-fishing",
            font=ctk.CTkFont(size=11), text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        self.tab_buttons: dict[str, ctk.CTkButton] = {}
        for name in self.TABS:
            btn = ctk.CTkButton(
                self.sidebar, text=name, anchor="w", height=36,
                fg_color="transparent", text_color=("gray20", "gray80"),
                hover_color=("gray80", "gray25"), corner_radius=8,
                command=lambda n=name: self._show_tab(n),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.tab_buttons[name] = btn

        ctk.CTkLabel(
            self.sidebar, text="Hradlen",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_MUTED,
        ).pack(side="bottom", anchor="w", padx=20, pady=(8, 14))

        self.content_holder = ctk.CTkFrame(self.root, fg_color="transparent")
        self.content_holder.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content_holder.grid_columnconfigure(0, weight=1)
        self.content_holder.grid_rowconfigure(0, weight=1)

        self.statusbar = ctk.CTkFrame(self.root, height=36, corner_radius=0)
        self.statusbar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.statusbar.grid_propagate(False)

        self.status_state = ctk.CTkLabel(
            self.statusbar, text="● STOPPED", text_color=COLOR_BAD,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.status_state.pack(side="left", padx=14)
        self.status_text = ctk.CTkLabel(self.statusbar, text="—", text_color=COLOR_MUTED)
        self.status_text.pack(side="left", padx=12)
        self.status_action = ctk.CTkLabel(self.statusbar, text="", text_color=COLOR_MUTED)
        self.status_action.pack(side="right", padx=14)

        self.frames: dict[str, ctk.CTkScrollableFrame] = {}

    def _make_tab(self, name: str) -> ctk.CTkScrollableFrame:
        f = ctk.CTkScrollableFrame(self.content_holder, label_text="")
        f.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        f.grid_remove()
        self.frames[name] = f
        return f

    def _show_tab(self, name: str):
        for n, f in self.frames.items():
            f.grid_remove()
            self.tab_buttons[n].configure(
                fg_color="transparent", text_color=("gray20", "gray80")
            )
        self.frames[name].grid()
        self.tab_buttons[name].configure(
            fg_color=COLOR_ACCENT, text_color="white"
        )
        self._current_tab = name

    def _section(self, parent: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
        wrap = ctk.CTkFrame(parent, corner_radius=12)
        wrap.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            wrap, text=title, anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(fill="x", padx=16, pady=(12, 8))
        inner = ctk.CTkFrame(wrap, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=(0, 12))
        return inner

    def _h1(self, parent, text: str):
        ctk.CTkLabel(
            parent, text=text, anchor="w",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(fill="x", pady=(0, 16))

    def _hint(self, parent, text: str):
        ctk.CTkLabel(
            parent, text=text, anchor="w", justify="left",
            text_color=COLOR_MUTED, font=ctk.CTkFont(size=11),
        ).pack(fill="x", padx=2, pady=(8, 0))

    def _build_tabs(self):
        self._build_main_tab(self._make_tab("Главная"))
        self._build_coords_tab(self._make_tab("Координаты"))
        self._build_timings_tab(self._make_tab("Тайминги"))
        self._build_hotkeys_tab(self._make_tab("Хоткеи"))
        self._build_stats_tab(self._make_tab("Статистика"))
        self._build_logs_tab(self._make_tab("Логи"))

    # --- Главная ---

    def _build_main_tab(self, p):
        head = ctk.CTkFrame(p, fg_color="transparent")
        head.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            head, text="Главная", anchor="w",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            head, text="Сохранить", command=lambda: self._save_tab("Главная"),
            width=130, height=32, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            head, text="Сбросить раздел", command=lambda: self._reset_tab("Главная"),
            width=160, height=32, corner_radius=8,
            fg_color="transparent", border_width=1,
            border_color=COLOR_MUTED, text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray25"),
        ).pack(side="right")

        ctk.CTkLabel(
            p, text=f"Управление: хоткей [{config.HOTKEY_TOGGLE}].",
            text_color=COLOR_MUTED, anchor="w",
        ).pack(fill="x", pady=(8, 16))

        tab_keys = []
        bait = self._section(p, "Наживка")
        f1 = LinkedField(
            bait, "INITIAL_BAIT_BUDGET",
            "Забросов до первой авто-закупки (≥ 1):",
            kind="int", validator=lambda v: v >= 1,
        )
        f1.pack(fill="x", pady=4)
        f2 = LinkedField(
            bait, "BUY_BAIT_COUNT",
            "Сколько закупать за раз (1..99):",
            kind="int", validator=lambda v: 1 <= v <= 99,
        )
        f2.pack(fill="x", pady=4)
        tab_keys.extend(["INITIAL_BAIT_BUDGET", "BUY_BAIT_COUNT"])
        self._hint(bait,
                   "Изменения применяются по кнопке «Сохранить» наверху.")

        toggles = self._section(p, "Авто-цикл")
        self.sw_auto_buy = LinkedSwitch(
            toggles, "AUTO_BUY_ENABLED", "Авто-закупка наживки",
            on_apply=self._on_auto_buy_changed,
        )
        self.sw_auto_buy.pack(anchor="w", pady=4)
        self.sw_auto_sell = LinkedSwitch(
            toggles, "AUTO_SELL_ENABLED", "Авто-продажа рыбы",
            on_apply=self._on_auto_sell_changed,
        )
        self.sw_auto_sell.pack(anchor="w", pady=4)
        tab_keys.extend(["AUTO_BUY_ENABLED", "AUTO_SELL_ENABLED"])
        self._hint(
            toggles,
            "Авто-продажа требует включённой авто-закупки\n"
            "(иначе после продажи бот остановится — закупать наживку нечем).",
        )

        behavior = self._section(p, "Поведение")
        self.sw_humanize = LinkedSwitch(
            behavior, "HUMANIZE",
            "Имитация человека (случайные паузы, разброс кликов и таймингов)",
        )
        self.sw_humanize.pack(anchor="w", pady=4)
        tab_keys.append("HUMANIZE")
        self._hint(
            behavior,
            "Снижает риск детекта по статистике сервера. Рекомендуется ВКЛ.",
        )

        ctrl = self._section(p, "Управление")
        ctk.CTkButton(
            ctrl, text="Сбросить счётчик наживки", command=self._reset_counter,
            width=240, height=34, corner_radius=10,
            fg_color="transparent", border_width=1,
            border_color=COLOR_MUTED, text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray25"),
        ).pack(anchor="w")

        ovl = self._section(p, "Оверлей")
        self.show_overlay_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(
            ovl, text="Показывать плавающий статус-оверлей поверх игры",
            variable=self.show_overlay_var, command=self._toggle_overlay,
        ).pack(anchor="w", pady=4)
        self._toggle_overlay()

        self._linked["Главная"] = [
            f1, f2,
            self.sw_auto_buy, self.sw_auto_sell,
            self.sw_humanize,
        ]

    def _on_auto_sell_changed(self, value: bool):
        if value and not self.sw_auto_buy.var.get():
            self.sw_auto_buy.set(True)

    def _on_auto_buy_changed(self, value: bool):
        if not value and self.sw_auto_sell.var.get():
            self.sw_auto_sell.set(False)

    def _reset_counter(self):
        if self.bot:
            self.bot._casts_remaining = config.INITIAL_BAIT_BUDGET
            print(f"[GUI] счётчик сброшен в {config.INITIAL_BAIT_BUDGET}")

    def _toggle_overlay(self):
        if self.show_overlay_var.get():
            if self.overlay is None:
                self.overlay = Overlay(parent=self.root)
        else:
            if self.overlay is not None:
                self.overlay.destroy()
                self.overlay = None

    def _build_coords_tab(self, p):
        head = ctk.CTkFrame(p, fg_color="transparent")
        head.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            head, text="Координаты", anchor="w",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            head, text="Сохранить", command=lambda: self._save_tab("Координаты"),
            width=130, height=32, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            head, text="Сбросить раздел", command=lambda: self._reset_tab("Координаты"),
            width=160, height=32, corner_radius=8,
            fg_color="transparent", border_width=1,
            border_color=COLOR_MUTED, text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray25"),
        ).pack(side="right")

        import presets
        preset_row = ctk.CTkFrame(p, fg_color="transparent")
        preset_row.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(preset_row, text="Готовый набор:", anchor="w").pack(side="left", padx=(0, 8))
        self._preset_var = tk.StringVar(value=presets.names()[0])
        ctk.CTkOptionMenu(
            preset_row, variable=self._preset_var, values=presets.names(),
            width=280,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            preset_row, text="Применить", command=self._apply_preset,
            width=130, height=32, corner_radius=8,
        ).pack(side="left")
        ctk.CTkLabel(
            p, text="Только заполнит поля — нажми «Сохранить» сверху чтобы записать.",
            text_color=COLOR_MUTED, font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(0, 14))

        widgets: list = []

        sell = self._section(p, "Продажа рыбы (открывается клавишей Q)")
        for key, lbl, hint in [
            ("SELL_TAB_STORAGE",  'Вкладка "Хранилище рыбы"', "внутри меню продажи"),
            ("SELL_QUICK_BUTTON", 'Кнопка "Быстрая продажа"', "внутри меню продажи"),
            ("SELL_CONFIRM",      'Кнопка "Подтвердить"',     "при продаже рыбы"),
        ]:
            w = LinkedPoint(sell, key, lbl, hint=hint)
            w.pack(fill="x", pady=6)
            widgets.append(w)

        buy = self._section(p, "Покупка наживки (открывается клавишей R)")
        for key, lbl, hint in [
            ("BUY_BAIT_PLUS",        'Кнопка "+"',          "внутри покупки наживки"),
            ("BUY_BAIT_CONFIRM",     'Кнопка "Купить"',     "внутри покупки наживки"),
            ("BUY_PURCHASE_CONFIRM", 'Кнопка "Подтвердить"', "в диалоге после Купить"),
        ]:
            w = LinkedPoint(buy, key, lbl, hint=hint)
            w.pack(fill="x", pady=6)
            widgets.append(w)

        bait = self._section(p, "Смена наживки (открывается клавишей E)")
        w = LinkedPoint(bait, "BAIT_SELECT_CONFIRM",
                        'Кнопка "Сменить"', hint="внутри меню смены наживки")
        w.pack(fill="x", pady=6); widgets.append(w)

        misc = self._section(p, "Прочее")
        w = LinkedPoint(misc, "CATCH_CLICK",
                        "Точка закрытия экрана награды",
                        hint="куда кликать чтобы закрыть экран после поимки рыбы")
        w.pack(fill="x", pady=6); widgets.append(w)

        roi = self._section(p, "Зоны экрана (для детекта)")
        w = LinkedROI(roi, "ROI_BAR", "Полоса QTE", hint="мини-игра по поимке рыбы")
        w.pack(fill="x", pady=6); widgets.append(w)

        grid = self._section(p, "Сетка магазина (для поиска нужной наживки)")
        w = LinkedROI(grid, "SHOP_GRID_ROI",
                      "Область с плитками наживок",
                      hint="выдели область из 9 плиток (3 колонки × 3 ряда)")
        w.pack(fill="x", pady=6); widgets.append(w)
        w = LinkedField(grid, "SHOP_GRID_COLS", "Колонок:", validator=lambda v: 1 <= v <= 10); w.pack(fill="x", pady=4); widgets.append(w)
        w = LinkedField(grid, "SHOP_GRID_ROWS", "Рядов:", validator=lambda v: 1 <= v <= 10); w.pack(fill="x", pady=4); widgets.append(w)
        w = LinkedField(grid, "BAIT_MATCH_THRESHOLD", "Порог совпадения шаблона (0..1):",
                        kind="float", validator=lambda v: 0 < v < 1); w.pack(fill="x", pady=4); widgets.append(w)

        self._linked["Координаты"] = widgets

    def _build_timings_tab(self, p):
        head = ctk.CTkFrame(p, fg_color="transparent")
        head.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            head, text="Тайминги (секунды)", anchor="w",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            head, text="Сохранить", command=lambda: self._save_tab("Тайминги"),
            width=130, height=32, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            head, text="Сбросить раздел", command=lambda: self._reset_tab("Тайминги"),
            width=160, height=32, corner_radius=8,
            fg_color="transparent", border_width=1,
            border_color=COLOR_MUTED, text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray25"),
        ).pack(side="right")

        widgets: list = []

        def add(parent, key, lbl, kind="float", **kw):
            w = LinkedField(parent, key, f"{lbl}:", kind=kind, **kw)
            w.pack(fill="x", pady=4)
            widgets.append(w)

        cycle = self._section(p, "Цикл рыбалки")
        for key, lbl in [
            ("CAST_DELAY", "Пауза после заброса"),
            ("MIN_BITE_WAIT", "Минимум ждать до первой подсечки"),
            ("STRIKE_INTERVAL", "Интервал между попытками подсечки"),
            ("MINIGAME_END_GRACE", "Пауза после исчезновения полосы"),
            ("MINIGAME_APPEAR_TIMEOUT", "Таймаут появления полосы"),
            ("POST_CATCH_COOLDOWN", "Кулдаун после пойманной"),
        ]:
            add(cycle, key, lbl)
        add(cycle, "STRIKE_MAX_ATTEMPTS", "Макс. попыток подсечки", kind="int")

        sell = self._section(p, "Продажа")
        for key, lbl in [
            ("SELL_OPEN_DELAY", "После Q (открытие меню)"),
            ("SELL_TAB_DELAY", "После клика по вкладке"),
            ("SELL_BUTTON_DELAY", "После Быстрая продажа"),
            ("SELL_CONFIRM_DELAY", "После Подтвердить"),
            ("SELL_CLOSE_DELAY", "После закрытия меню"),
        ]:
            add(sell, key, lbl)

        buy = self._section(p, "Покупка")
        for key, lbl in [
            ("BUY_OPEN_DELAY", "После R (открытие меню)"),
            ("BUY_SELECT_DELAY", "После выбора плитки"),
            ("BUY_PLUS_INTERVAL", "Интервал между нажатиями +"),
            ("BUY_PURCHASE_DELAY", "После Купить до Подтвердить"),
            ("BUY_CLOSE_DELAY", "После закрытия меню"),
        ]:
            add(buy, key, lbl)

        bait = self._section(p, "Смена наживки")
        for key, lbl in [
            ("BAIT_SELECT_OPEN_DELAY", "После E"),
            ("BAIT_SELECT_CONFIRM_DELAY", "После Сменить"),
        ]:
            add(bait, key, lbl)

        qte = self._section(p, "QTE")
        add(qte, "HOLD_TRIGGER_PX", "Порог тяги (px)", kind="int")
        add(qte, "RELEASE_BIAS_PX", "Случайный сдвиг отпускания (±px)", kind="int")
        add(qte, "TICK_INTERVAL", "Tick главного цикла")

        self._linked["Тайминги"] = widgets

    def _save_tab(self, tab_name: str):
        widgets = self._linked.get(tab_name, [])
        errors: list[str] = []
        validatable = [w for w in widgets if hasattr(w, "validate")]
        for w in validatable:
            ok, err = w.validate()
            if not ok:
                errors.append(err)
        if errors:
            from tkinter import messagebox
            messagebox.showerror(
                "Ошибка валидации",
                "Нельзя сохранить — есть ошибки:\n\n" + "\n".join(errors),
            )
            return
        for w in validatable:
            try:
                w.apply()
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Ошибка", f"При сохранении: {e}")
                return
        print(f"[GUI] '{tab_name}' сохранён")

    def _apply_preset(self):
        import presets
        name = self._preset_var.get()
        preset = presets.get(name)
        if not preset:
            return
        widgets = self._linked.get("Координаты", [])
        applied = 0
        for w in widgets:
            key = getattr(w, "config_key", None)
            if key and key in preset:
                try:
                    w.set_value(preset[key])
                    applied += 1
                except Exception as e:
                    print(f"[GUI] failed {key}: {e}")
        print(f"[GUI] пресет '{name}' заполнен ({applied})")

    def _reset_tab(self, tab_name: str):
        widgets = self._linked.get(tab_name, [])
        keys = [w.config_key for w in widgets if hasattr(w, "config_key")]
        if not keys:
            return
        settings.reset_keys(config, keys)
        for w in widgets:
            try:
                w.refresh()
            except Exception:
                pass
        print(f"[GUI] '{tab_name}' сброшен")

    HOTKEY_KEYS = (
        ("HOTKEY_TOGGLE", "Старт / стоп"),
        ("HOTKEY_QUIT", "Выход"),
        ("HOTKEY_SELL", "Разовая продажа"),
        ("HOTKEY_BUY_BAIT", "Разовая покупка"),
        ("HOTKEY_TOGGLE_AUTO_SELL", "Тумблер авто-продажи"),
        ("HOTKEY_TOGGLE_AUTO_BUY", "Тумблер авто-закупки"),
    )

    def _build_hotkeys_tab(self, p):
        head = ctk.CTkFrame(p, fg_color="transparent")
        head.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            head, text="Хоткеи", anchor="w",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            head, text="Сохранить", command=self._save_hotkeys,
            width=130, height=32, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            head, text="Сбросить раздел", command=self._reset_hotkeys,
            width=160, height=32, corner_radius=8,
            fg_color="transparent", border_width=1,
            border_color=COLOR_MUTED, text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray25"),
        ).pack(side="right")

        sec = self._section(p, "Клавиши")
        self.hk_vars: dict[str, tk.StringVar] = {}
        self.hk_buttons: dict[str, ctk.CTkButton] = {}

        for key, label in self.HOTKEY_KEYS:
            row = ctk.CTkFrame(sec, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label, anchor="w", width=240).pack(side="left")

            var = tk.StringVar(value=str(getattr(config, key)))
            self.hk_vars[key] = var
            ctk.CTkLabel(
                row, textvariable=var, anchor="center", width=80,
                fg_color=("gray85", "gray25"), corner_radius=6,
            ).pack(side="left", padx=8)

            btn = ctk.CTkButton(
                row, text="Изменить",
                width=110, height=28, corner_radius=8,
                command=lambda k=key: self._capture_hotkey(k),
            )
            btn.pack(side="left", padx=4)
            self.hk_buttons[key] = btn

        self._hint(
            sec,
            "Нажми «Изменить», потом нужную клавишу. Применяется по «Сохранить».\n"
            "Буквы, цифры, F1-F12, esc, space, enter и т.п.",
        )

    def _save_hotkeys(self):
        from tkinter import messagebox
        new_values: dict[str, str] = {}
        seen: dict[str, str] = {}
        errors: list[str] = []
        for key, _label in self.HOTKEY_KEYS:
            v = self.hk_vars[key].get().strip()
            if not v or v == "…":
                errors.append(f"{key}: пусто")
                continue
            if v in seen:
                errors.append(f"{key} и {seen[v]} на одной клавише '{v}'")
                continue
            seen[v] = key
            new_values[key] = v
        if errors:
            messagebox.showerror("Ошибка", "Нельзя сохранить:\n\n" + "\n".join(errors))
            return
        for k, v in new_values.items():
            setattr(config, k, v)
            settings.save_one(k, v)
        print("[GUI] хоткеи сохранены")

    def _reset_hotkeys(self):
        keys = [k for k, _ in self.HOTKEY_KEYS]
        settings.reset_keys(config, keys)
        for key in keys:
            self.hk_vars[key].set(str(getattr(config, key)))
        print("[GUI] хоткеи сброшены")

    def _capture_hotkey(self, config_key: str):
        if self._capturing_for is not None:
            return
        self._capturing_for = config_key
        self.hk_buttons[config_key].configure(text="Нажми клавишу…", state="disabled")
        self.hk_vars[config_key].set("…")

        def _wait():
            try:
                event = keyboard.read_event(suppress=False)
                while event.event_type != keyboard.KEY_DOWN:
                    event = keyboard.read_event(suppress=False)
                key_name = event.name or ""
                if not key_name:
                    return
                self.root.after(0, self._capture_done, config_key, key_name)
            except Exception as e:
                self.root.after(0, self._capture_done, config_key, None, str(e))

        threading.Thread(target=_wait, daemon=True).start()

    def _capture_done(self, config_key: str, key_name: str | None, err: str | None = None):
        self._capturing_for = None
        btn = self.hk_buttons[config_key]
        btn.configure(text="Изменить", state="normal")
        if key_name is None:
            self.hk_vars[config_key].set(str(getattr(config, config_key)))
            print(f"[GUI] capture failed: {err}")
            return
        self.hk_vars[config_key].set(key_name)
        print(f"[GUI] {config_key} = {key_name}")

    def _build_stats_tab(self, p):
        self._h1(p, "Статистика")

        sec_total = self._section(p, "За всё время")
        self.lbl_total_catches = self._stat_row(sec_total, "Поймано рыб (все сессии):")
        self.lbl_total_casts = self._stat_row(sec_total, "Всего забросов:")
        self.lbl_total_rate = self._stat_row(sec_total, "Успешность:")

        sec_sess = self._section(p, "Текущая сессия")
        self.lbl_sess_catches = self._stat_row(sec_sess, "Поймано рыб:")
        self.lbl_sess_casts = self._stat_row(sec_sess, "Забросов:")
        self.lbl_sess_rate = self._stat_row(sec_sess, "Успешность:")
        self.lbl_sess_minutes = self._stat_row(sec_sess, "Длительность:")
        self.lbl_sess_fph = self._stat_row(sec_sess, "Рыб/час:")
        self.lbl_sess_avg_react = self._stat_row(sec_sess, "Средняя реакция:")
        self.lbl_sess_avg_minigame = self._stat_row(sec_sess, "Средний QTE:")

        self._refresh_stats()

    def _stat_row(self, parent, label: str) -> ctk.CTkLabel:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(row, text=label, anchor="w", width=300).pack(side="left")
        v = ctk.CTkLabel(
            row, text="—", anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_ACCENT,
        )
        v.pack(side="left", padx=8)
        return v

    def _refresh_stats(self):
        if self._quit:
            return
        try:
            from stats import lifetime_total_catches, lifetime_total_casts
            total_catches = lifetime_total_catches()
            total_casts = lifetime_total_casts()
            self.lbl_total_catches.configure(text=f"{total_catches} рыб")
            self.lbl_total_casts.configure(text=str(total_casts))
            rate = (total_catches / total_casts * 100.0) if total_casts else 0.0
            self.lbl_total_rate.configure(text=f"{rate:.0f}%")
        except Exception as e:
            self.lbl_total_catches.configure(text=f"err: {e}")

        if self.bot is not None:
            s = self.bot.stats
            self.lbl_sess_catches.configure(text=f"{s.catches} рыб")
            self.lbl_sess_casts.configure(text=str(s.casts))
            self.lbl_sess_rate.configure(text=f"{s.success_rate()*100:.0f}%")
            self.lbl_sess_minutes.configure(text=f"{s.session_minutes():.1f} мин")
            self.lbl_sess_fph.configure(text=f"{s.fish_per_hour():.1f} /ч")
            ar = s.avg_reaction_ms()
            self.lbl_sess_avg_react.configure(text=f"{ar:.0f} мс" if ar else "—")
            am = s.avg_minigame_s()
            self.lbl_sess_avg_minigame.configure(text=f"{am:.1f} с" if am else "—")
        else:
            for lbl in (self.lbl_sess_catches, self.lbl_sess_casts, self.lbl_sess_rate,
                        self.lbl_sess_minutes, self.lbl_sess_fph,
                        self.lbl_sess_avg_react, self.lbl_sess_avg_minigame):
                lbl.configure(text="—")

        self.root.after(1500, self._refresh_stats)

    # --- Логи ---

    def _build_logs_tab(self, p):
        self._h1(p, "Логи")

        ctrl = ctk.CTkFrame(p, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            ctrl, text="Скопировать всё", command=self._copy_logs,
            width=140, height=30, corner_radius=8,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            ctrl, text="Очистить", command=self._clear_logs,
            width=100, height=30, corner_radius=8,
            fg_color="transparent", border_width=1,
            border_color=COLOR_MUTED, text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray25"),
        ).pack(side="left")
        self.lbl_copy_status = ctk.CTkLabel(
            ctrl, text="", text_color=COLOR_OK,
            font=ctk.CTkFont(size=11),
        )
        self.lbl_copy_status.pack(side="left", padx=10)

        self.log_text = ctk.CTkTextbox(
            p, wrap="word", font=("Consolas", 11),
            corner_radius=10,
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

        sys.stdout = _TextStream(self.log_text, sys.__stdout__)
        sys.stderr = _TextStream(self.log_text, sys.__stderr__)

    def _clear_logs(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _copy_logs(self):
        try:
            text = self.log_text.get("1.0", "end").rstrip()
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.lbl_copy_status.configure(text=f"скопировано {len(text)} символов")
            self.root.after(2500, lambda: self.lbl_copy_status.configure(text=""))
        except Exception as e:
            self.lbl_copy_status.configure(text=f"ошибка: {e}", text_color=COLOR_BAD)

    def _toggle_running(self):
        if time.time() - self._last_toggle_ts < 0.4:
            return
        self._last_toggle_ts = time.time()
        self._running = not self._running
        if self._running:
            if self.bot is None:
                self.bot = FishingBot()
            print("--- ВКЛ ---")
        else:
            if self.bot is not None:
                self.bot.cleanup()
            print("--- ВЫКЛ ---")

    def _bot_loop(self):
        while not self._quit:
            if self._running and self.bot is not None:
                try:
                    self.bot.tick()
                    if self.bot._should_stop:
                        self.bot._should_stop = False
                        self._running = False
                        self.bot.cleanup()
                        print("--- АВТОСТОП ---")
                except Exception as e:
                    print(f"Ошибка в bot.tick(): {e}")
                    self._running = False
                    if self.bot:
                        self.bot.last_action = f"ERROR: {e}"
            time.sleep(config.TICK_INTERVAL)

    def _gui_is_foreground(self) -> bool:
        if _user32 is None:
            return False
        try:
            fg = _user32.GetForegroundWindow()
            if fg == self.root.winfo_id():
                return True
            if self.overlay is not None and fg == self.overlay.root.winfo_id():
                return True
            return False
        except Exception:
            return False

    def _hotkey_loop(self):
        last = {k: 0.0 for k in ("quit", "sell", "buy", "auto_sell", "auto_buy", "toggle")}
        while not self._quit:
            try:
                if self._gui_is_foreground():
                    time.sleep(0.05)
                    continue
                now = time.time()
                if keyboard.is_pressed(config.HOTKEY_TOGGLE) and now - last["toggle"] > 0.4:
                    last["toggle"] = now
                    self._toggle_running()
                if self.bot is not None:
                    if keyboard.is_pressed(config.HOTKEY_SELL) and now - last["sell"] > 1:
                        last["sell"] = now
                        self.bot.request_sell()
                    if keyboard.is_pressed(config.HOTKEY_BUY_BAIT) and now - last["buy"] > 1:
                        last["buy"] = now
                        self.bot.request_buy_bait()
                if keyboard.is_pressed(config.HOTKEY_TOGGLE_AUTO_SELL) and now - last["auto_sell"] > 0.5:
                    last["auto_sell"] = now
                    new = not config.AUTO_SELL_ENABLED
                    config.AUTO_SELL_ENABLED = new
                    settings.save_one("AUTO_SELL_ENABLED", new)
                    self.sw_auto_sell.var.set(new)
                if keyboard.is_pressed(config.HOTKEY_TOGGLE_AUTO_BUY) and now - last["auto_buy"] > 0.5:
                    last["auto_buy"] = now
                    new = not config.AUTO_BUY_ENABLED
                    config.AUTO_BUY_ENABLED = new
                    settings.save_one("AUTO_BUY_ENABLED", new)
                    self.sw_auto_buy.var.set(new)
                if keyboard.is_pressed(config.HOTKEY_QUIT) and now - last["quit"] > 1:
                    last["quit"] = now
                    self._on_close()
                    return
            except Exception:
                pass
            time.sleep(0.05)

    # ---------- status update ----------

    def _update_status(self):
        if self._quit:
            return
        if self._running:
            self.status_state.configure(text="● RUNNING", text_color=COLOR_OK)
        else:
            self.status_state.configure(text="● STOPPED", text_color=COLOR_BAD)

        if self.bot is not None:
            stats = self.bot.stats
            session_info = (
                self.bot.session.status() if self.bot.session
                else f"всего: {stats.session_minutes():.1f} мин"
            )
            txt = (
                f"{stats.short_summary()}    "
                f"наживки: {self.bot._casts_remaining}    "
                f"state: {self.bot.state.name}    {session_info}"
            )
            self.status_text.configure(text=txt)
            self.status_action.configure(text=self.bot.last_action[:80])

            if self.overlay is not None:
                avg_react = stats.avg_reaction_ms()
                ovl_session = session_info
                if avg_react:
                    ovl_session += f"  ~{avg_react:.0f}мс"
                self.overlay.update(
                    running=self._running,
                    state=self.bot.state.name,
                    action=self.bot.last_action,
                    stats_summary=stats.short_summary(),
                    session_info=ovl_session,
                    auto_sell=config.AUTO_SELL_ENABLED,
                    auto_buy=config.AUTO_BUY_ENABLED,
                    bait_left=self.bot._casts_remaining,
                )

        self.root.after(250, self._update_status)

    def _on_close(self):
        self._quit = True
        self._running = False
        try:
            if self.bot:
                self.bot.cleanup()
        except Exception:
            pass
        try:
            if self.overlay:
                self.overlay.destroy()
                self.overlay = None
        except Exception:
            pass
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        # CTk шумит TclError при разрушении — глушим.
        try:
            self.root.report_callback_exception = lambda *a, **k: None
        except Exception:
            pass
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()
