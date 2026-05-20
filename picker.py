from __future__ import annotations

import threading
import time
import tkinter as tk
from pathlib import Path
from typing import Callable, Optional

import cv2
import customtkinter as ctk
import keyboard
import mss
import numpy as np
from PIL import Image, ImageTk

from paths import resource_dir


PREVIEW_MAX_W = 1100
PREVIEW_MAX_H = 580


def _grab_full_screen() -> np.ndarray:
    sct = mss.mss()
    mon = sct.monitors[1]
    raw = np.array(sct.grab(mon))
    sct.close()
    return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)


class _BasePicker:
    KIND = "point"  # "point" | "roi"

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        on_done: Callable[[Optional[object]], None],
        example_image_path: Optional[str] = None,
        instruction: str = "",
    ):
        self.parent = parent
        self.title = title
        self.on_done = on_done
        self.example_image_path = example_image_path
        self.instruction = instruction or self._default_instruction()

        self._screenshot: Optional[np.ndarray] = None
        self._preview_photo: Optional[ImageTk.PhotoImage] = None
        self._example_photo: Optional[ImageTk.PhotoImage] = None
        self._preview_scale = 1.0
        self._captured_value = None
        self._space_hook = None
        self._closed = False
        self._roi_start: Optional[tuple[int, int]] = None

        self.window = ctk.CTkToplevel(parent)
        self.window.title(title)
        self.window.geometry("1200x780")
        self.window.attributes("-topmost", True)
        self.window.protocol("WM_DELETE_WINDOW", self._cancel)
        self.window.transient(parent)

        try:
            ico = resource_dir() / "icon.ico"
            if ico.exists():
                # delay из-за race с инициализацией CTk
                self.window.after(220, lambda p=str(ico): self.window.iconbitmap(p))
        except Exception:
            pass
        self.window.after(100, self._grab_modal)

        self._show_step1_instructions()

    def _grab_modal(self):
        try:
            self.window.grab_set()
        except Exception:
            pass

    def _default_instruction(self) -> str:
        if self.KIND == "point":
            return ("Кликни по нужной точке. Можно перекликнуть — "
                    "берётся последняя точка.")
        return ("Выдели прямоугольник: зажми ЛКМ и потяни "
                "от одного угла к другому.")

    def _show_step1_instructions(self):
        self._clear_window()

        ctk.CTkLabel(
            self.window, text=self.title,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            self.window, text="Шаг 1 из 3 — пример",
            text_color="#888", font=ctk.CTkFont(size=12),
        ).pack(pady=(0, 12))

        if self.example_image_path and Path(self.example_image_path).exists():
            try:
                img = Image.open(self.example_image_path)
                img.thumbnail((900, 380))
                self._example_photo = ImageTk.PhotoImage(img)
                ctk.CTkLabel(self.window, image=self._example_photo, text="").pack(pady=8)
            except Exception as e:
                ctk.CTkLabel(self.window, text=f"(пример не загружен: {e})",
                             text_color="#888").pack()
        else:
            ph = ctk.CTkFrame(self.window, fg_color=("gray85", "gray20"),
                              width=900, height=200, corner_radius=12)
            ph.pack(pady=8)
            ph.pack_propagate(False)
            ctk.CTkLabel(
                ph, text="(пример отсутствует)",
                text_color="#888",
            ).pack(expand=True)

        ctk.CTkLabel(
            self.window, text=self.instruction,
            wraplength=900, justify="left",
        ).pack(pady=(12, 4), padx=20)

        ctk.CTkLabel(
            self.window,
            text="Дальше переключись на игру и нажми ПРОБЕЛ — будет скриншот экрана.",
            text_color="#888", wraplength=900, justify="center",
        ).pack(pady=(4, 12), padx=20)

        row = ctk.CTkFrame(self.window, fg_color="transparent")
        row.pack(pady=12)
        ctk.CTkButton(
            row, text="Дальше — захват экрана",
            width=240, height=40, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._show_step2_capture,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            row, text="Отмена",
            width=120, height=40, corner_radius=10,
            fg_color="transparent", border_width=1,
            command=self._cancel,
        ).pack(side="left", padx=4)

    def _show_step2_capture(self):
        self._clear_window()

        ctk.CTkLabel(
            self.window, text=self.title,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            self.window, text="Шаг 2 из 3 — снимок экрана",
            text_color="#888", font=ctk.CTkFont(size=12),
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            self.window,
            text=("1. Переключись на игру.\n"
                  "2. Нажми ПРОБЕЛ — будет скриншот."),
            justify="center", font=ctk.CTkFont(size=14),
        ).pack(pady=20)

        self._wait_lbl = ctk.CTkLabel(
            self.window, text="Жду ПРОБЕЛ…",
            text_color="#22c55e", font=ctk.CTkFont(size=14, weight="bold"),
        )
        self._wait_lbl.pack(pady=8)

        ctk.CTkButton(
            self.window, text="Назад", width=120, height=36, corner_radius=10,
            fg_color="transparent", border_width=1,
            command=self._show_step1_instructions,
        ).pack(pady=4)
        ctk.CTkButton(
            self.window, text="Отмена", width=120, height=36, corner_radius=10,
            fg_color="transparent", border_width=1,
            command=self._cancel,
        ).pack(pady=4)

        self._setup_space_listener()

    def _setup_space_listener(self):
        self._remove_space_listener()
        try:
            self._space_hook = keyboard.on_press_key("space", self._on_space, suppress=False)
        except Exception as e:
            print(f"[picker] space hook failed: {e}")

    def _remove_space_listener(self):
        if self._space_hook is not None:
            try:
                keyboard.unhook(self._space_hook)
            except Exception:
                pass
            self._space_hook = None

    def _on_space(self, event):
        if self._closed:
            return
        self._remove_space_listener()
        self.window.after(0, self._do_capture)

    def _do_capture(self):
        if self._closed:
            return
        try:
            self.window.withdraw()
            try:
                self.parent.update_idletasks()
            except Exception:
                pass
            time.sleep(0.25)
            self._screenshot = _grab_full_screen()
        except Exception as e:
            print(f"[picker] screenshot error: {e}")
        finally:
            try:
                self.window.deiconify()
                self.window.lift()
                self.window.focus_force()
            except Exception:
                pass
        if self._screenshot is None:
            return
        self._show_step3_select()

    def _show_step3_select(self):
        self._clear_window()

        ctk.CTkLabel(
            self.window, text=self.title,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(12, 4))
        ctk.CTkLabel(
            self.window, text="Шаг 3 из 3 — укажи место",
            text_color="#888", font=ctk.CTkFont(size=12),
        ).pack(pady=(0, 8))

        ctk.CTkLabel(self.window, text=self.instruction, wraplength=1100).pack(pady=(0, 8))

        h, w = self._screenshot.shape[:2]
        scale = min(PREVIEW_MAX_W / w, PREVIEW_MAX_H / h, 1.0)
        pw = max(1, int(w * scale))
        ph = max(1, int(h * scale))
        self._preview_scale = scale

        rgb = cv2.cvtColor(self._screenshot, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        if scale != 1.0:
            pil = pil.resize((pw, ph), Image.LANCZOS)
        self._preview_photo = ImageTk.PhotoImage(pil)

        self.canvas = tk.Canvas(
            self.window, width=pw, height=ph,
            bg="#1a1a1a", highlightthickness=1, highlightbackground="#444",
        )
        self.canvas.pack(pady=4)
        self.canvas.create_image(0, 0, anchor="nw", image=self._preview_photo)

        if self.KIND == "point":
            self.canvas.bind("<Button-1>", self._on_click_point)
        else:
            self.canvas.bind("<ButtonPress-1>", self._on_roi_press)
            self.canvas.bind("<B1-Motion>", self._on_roi_drag)
            self.canvas.bind("<ButtonRelease-1>", self._on_roi_release)

        self.lbl_value = ctk.CTkLabel(
            self.window, text="—",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#3b82f6",
        )
        self.lbl_value.pack(pady=8)

        row = ctk.CTkFrame(self.window, fg_color="transparent")
        row.pack(pady=8)
        self.btn_confirm = ctk.CTkButton(
            row, text="Подтвердить", width=180, height=40, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._confirm, state="disabled",
        )
        self.btn_confirm.pack(side="left", padx=4)
        ctk.CTkButton(
            row, text="Снять заново", width=160, height=40, corner_radius=10,
            fg_color="transparent", border_width=1,
            command=self._show_step2_capture,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            row, text="Отмена", width=120, height=40, corner_radius=10,
            fg_color="transparent", border_width=1,
            command=self._cancel,
        ).pack(side="left", padx=4)

    def _on_click_point(self, event):
        sx = int(event.x / self._preview_scale)
        sy = int(event.y / self._preview_scale)
        self._captured_value = (sx, sy)
        self.canvas.delete("marker")
        self.canvas.create_oval(event.x - 10, event.y - 10, event.x + 10, event.y + 10,
                                outline="#22c55e", width=3, tags="marker")
        self.canvas.create_line(event.x - 14, event.y, event.x + 14, event.y,
                                fill="#22c55e", width=2, tags="marker")
        self.canvas.create_line(event.x, event.y - 14, event.x, event.y + 14,
                                fill="#22c55e", width=2, tags="marker")
        self.lbl_value.configure(text=f"x={sx}  y={sy}")
        self.btn_confirm.configure(state="normal")

    def _on_roi_press(self, event):
        self._roi_start = (event.x, event.y)
        self.canvas.delete("marker")

    def _on_roi_drag(self, event):
        if self._roi_start is None:
            return
        x0, y0 = self._roi_start
        self.canvas.delete("marker")
        self.canvas.create_rectangle(
            x0, y0, event.x, event.y,
            outline="#22c55e", width=3, tags="marker",
        )

    def _on_roi_release(self, event):
        if self._roi_start is None:
            return
        x0, y0 = self._roi_start
        self._roi_start = None
        x1, y1 = event.x, event.y
        l_canvas = min(x0, x1)
        t_canvas = min(y0, y1)
        r_canvas = max(x0, x1)
        b_canvas = max(y0, y1)
        if r_canvas - l_canvas < 4 or b_canvas - t_canvas < 4:
            return
        s = self._preview_scale
        roi = {
            "left": int(l_canvas / s),
            "top": int(t_canvas / s),
            "width": int((r_canvas - l_canvas) / s),
            "height": int((b_canvas - t_canvas) / s),
        }
        self._captured_value = roi
        self.lbl_value.configure(
            text=f"L={roi['left']}  T={roi['top']}  W={roi['width']}  H={roi['height']}"
        )
        self.btn_confirm.configure(state="normal")

    def _confirm(self):
        if self._captured_value is None:
            return
        self._closed = True
        self._remove_space_listener()
        try:
            self.window.grab_release()
            self.window.destroy()
        except Exception:
            pass
        self.on_done(self._captured_value)

    def _cancel(self):
        if self._closed:
            return
        self._closed = True
        self._remove_space_listener()
        try:
            self.window.grab_release()
            self.window.destroy()
        except Exception:
            pass
        self.on_done(None)

    def _clear_window(self):
        for w in self.window.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass


class PointPicker(_BasePicker):
    KIND = "point"


class RoiPicker(_BasePicker):
    KIND = "roi"
