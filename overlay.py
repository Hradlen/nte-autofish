import tkinter as tk


class Overlay:
    def __init__(self, parent: tk.Misc | None = None):
        if parent is None:
            self.root = tk.Tk()
            self._owns_root = True
        else:
            self.root = tk.Toplevel(parent)
            self._owns_root = False
        self.root.title("NTE Fish")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.85)
        self.root.configure(bg="#000000")

        # Правый верх — не пересекается с ROI шопа (x=37..677) и QTE.
        self.root.geometry("320x230+1590+10")

        font_title = ("Consolas", 13, "bold")
        font_body = ("Consolas", 10)
        font_small = ("Consolas", 9)

        self.lbl_status = tk.Label(
            self.root, text="● STOPPED", fg="#ff5555", bg="#000000",
            font=font_title, anchor="w", padx=10, pady=2,
        )
        self.lbl_status.pack(fill="x")

        self.lbl_state = tk.Label(
            self.root, text="state: -", fg="#55ddff", bg="#000000",
            font=font_body, anchor="w", padx=10,
        )
        self.lbl_state.pack(fill="x")

        self.lbl_stats = tk.Label(
            self.root, text="0 рыб  0.0/ч  0%", fg="#ffffff", bg="#000000",
            font=font_body, anchor="w", padx=10,
        )
        self.lbl_stats.pack(fill="x")

        self.lbl_session = tk.Label(
            self.root, text="session: -", fg="#bbbbbb", bg="#000000",
            font=font_small, anchor="w", padx=10,
        )
        self.lbl_session.pack(fill="x")

        self.lbl_auto = tk.Label(
            self.root, text="auto: SELL  BUY", fg="#aaffaa", bg="#000000",
            font=font_small, anchor="w", padx=10,
        )
        self.lbl_auto.pack(fill="x")

        self.lbl_bait = tk.Label(
            self.root, text="наживки: -", fg="#ffcc66", bg="#000000",
            font=font_body, anchor="w", padx=10,
        )
        self.lbl_bait.pack(fill="x")

        self.lbl_action = tk.Label(
            self.root, text="action: -", fg="#ffdd55", bg="#000000",
            font=font_body, anchor="w", padx=10,
        )
        self.lbl_action.pack(fill="x")

        self.lbl_hint = tk.Label(
            self.root, text="перетащи чтобы переместить",
            fg="#888888", bg="#000000", font=("Consolas", 8), anchor="w", padx=10,
        )
        self.lbl_hint.pack(fill="x", pady=(2, 0))

        for w in (self.root, self.lbl_status, self.lbl_state,
                  self.lbl_stats, self.lbl_session, self.lbl_auto,
                  self.lbl_bait, self.lbl_action, self.lbl_hint):
            w.bind("<Button-1>", self._on_press)
            w.bind("<B1-Motion>", self._on_drag)

        self._drag_x = 0
        self._drag_y = 0

    def _on_press(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_drag(self, event):
        nx = event.x_root - self._drag_x
        ny = event.y_root - self._drag_y
        self.root.geometry(f"+{nx}+{ny}")

    def update(self, *, running: bool, state: str, action: str,
               stats_summary: str = "", session_info: str = "",
               auto_sell: bool = True, auto_buy: bool = True,
               bait_left: int | None = None):
        if running:
            self.lbl_status.config(text="● RUNNING", fg="#55ff55")
        else:
            self.lbl_status.config(text="● STOPPED", fg="#ff5555")
        self.lbl_state.config(text=f"state: {state}")
        self.lbl_stats.config(text=stats_summary or "0 рыб  0.0/ч  0%")
        self.lbl_session.config(text=session_info or "session: -")

        sell_str = "ON" if auto_sell else "off"
        buy_str = "ON" if auto_buy else "off"
        either_off = (not auto_sell) or (not auto_buy)
        import config
        self.lbl_auto.config(
            text=f"авто-продажа: {sell_str}  ·  авто-закупка: {buy_str}",
            fg="#ffaa55" if either_off else "#aaffaa",
        )

        if bait_left is not None:
            self.lbl_bait.config(text=f"наживки осталось: {bait_left}")

        self.lbl_action.config(text=f"action: {action}")

    def schedule(self, ms: int, callback) -> None:
        self.root.after(ms, callback)

    def mainloop(self) -> None:
        self.root.mainloop()

    def destroy(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass
