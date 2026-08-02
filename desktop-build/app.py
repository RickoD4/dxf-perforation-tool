"""
PerfoStudio Desktop — генератор перфорации из изображения (offline-версия).

Полный перенос логики и интерфейса веб-приложения PerfoStudio на Python + tkinter:
    - загрузка изображения (PNG/JPG/BMP)
    - настройка шага сетки, диаметров отверстий, чувствительности,
      порога отсечения, формы (круг/квадрат/шестиугольник), шахматного
      порядка и инверсии яркости
    - настройки G-code (подача, врезание, безопасная высота, глубина реза,
      диаметр фрезы, обороты шпинделя)
    - каждое значение можно как двигать ползунком, так и напечатать вручную
    - живой предпросмотр перфорации на canvas
    - экспорт в DXF, SVG, CSV и G-code

Диапазоны и шаги полей синхронизированы с веб-версией
(src/components/perfo/Sidebar.tsx).

Сборка в .exe: python build.py app.py PerfoStudio
(или просто дважды кликните СОБРАТЬ.bat)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Optional

from PIL import Image, ImageTk

from perfo_core import (
    PerfoSettings,
    GCodeSettings,
    DEFAULT_SETTINGS,
    DEFAULT_GCODE,
    generate_perforation,
    shape_vertices,
    to_dxf,
    to_svg,
    to_csv,
    to_gcode,
)


class SliderField:
    """Строка "слайдер + поле для ввода числа" с двусторонней синхронизацией.

    Пользователь может как двигать ползунок, так и напрямую напечатать
    значение в поле — оба способа работают эквивалентно, как на сайте.
    """

    def __init__(
        self,
        parent: ttk.Frame,
        label: str,
        lo: float,
        hi: float,
        step: float,
        value: float,
        unit: str = "",
        on_change: Optional[Callable[[], None]] = None,
    ) -> None:
        self.lo = lo
        self.hi = hi
        self.step = step
        self.on_change = on_change
        self._updating = False  # защита от рекурсии при синхронизации

        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)

        header = ttk.Frame(row)
        header.pack(fill="x")
        ttk.Label(header, text=f"{label}{f', {unit}' if unit else ''}").pack(side="left")

        self.var = tk.DoubleVar(value=value)
        self.entry_var = tk.StringVar(value=self._fmt(value))

        entry = ttk.Entry(header, textvariable=self.entry_var, width=8, justify="right")
        entry.pack(side="right")
        entry.bind("<Return>", self._on_entry_commit)
        entry.bind("<FocusOut>", self._on_entry_commit)

        self.scale = ttk.Scale(
            row, from_=lo, to=hi, orient="horizontal", variable=self.var,
            command=self._on_scale_move,
        )
        self.scale.pack(fill="x", pady=(2, 0))

    def _fmt(self, v: float) -> str:
        # Целые значения без десятичной точки (например 8, а не 8.0),
        # дробные — с точностью до сотых.
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return f"{v:.2f}".rstrip("0").rstrip(".")

    def _clamp(self, v: float) -> float:
        return max(self.lo, min(self.hi, v))

    def _on_scale_move(self, _val: str) -> None:
        if self._updating:
            return
        self._updating = True
        v = self._clamp(self.var.get())
        self.entry_var.set(self._fmt(v))
        self._updating = False
        if self.on_change:
            self.on_change()

    def _on_entry_commit(self, _event=None) -> None:
        if self._updating:
            return
        try:
            v = float(self.entry_var.get().replace(",", "."))
        except ValueError:
            v = self.var.get()
        v = self._clamp(v)
        self._updating = True
        self.var.set(v)
        self.entry_var.set(self._fmt(v))
        self._updating = False
        if self.on_change:
            self.on_change()

    def get(self) -> float:
        return self.var.get()

    def set(self, v: float) -> None:
        v = self._clamp(v)
        self._updating = True
        self.var.set(v)
        self.entry_var.set(self._fmt(v))
        self._updating = False

    def set_range(self, lo: float, hi: float) -> None:
        """Обновляет min/max (для динамических диапазонов, например
        minHole зависит от maxHole, как на сайте)."""
        self.lo, self.hi = lo, hi
        self.scale.configure(from_=lo, to=hi)
        clamped = self._clamp(self.get())
        if clamped != self.get():
            self.set(clamped)


class PerfoStudioApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PerfoStudio — image → vector DXF")
        self.root.geometry("1280x800")
        self.root.minsize(960, 640)

        self.image: Optional[Image.Image] = None
        self.result = None
        self._thumb_photo = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        # Прокручиваемый сайдбар (настроек много — как на сайте)
        sidebar_outer = ttk.Frame(container, width=340)
        sidebar_outer.pack(side="left", fill="y", padx=8, pady=8)
        sidebar_outer.pack_propagate(False)

        sidebar_canvas = tk.Canvas(sidebar_outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(sidebar_outer, orient="vertical", command=sidebar_canvas.yview)
        sidebar = ttk.Frame(sidebar_canvas)

        sidebar.bind(
            "<Configure>",
            lambda _e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")),
        )
        sidebar_canvas.create_window((0, 0), window=sidebar, anchor="nw", width=316)
        sidebar_canvas.configure(yscrollcommand=scrollbar.set)
        sidebar_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        sidebar_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas_area = ttk.Frame(container)
        canvas_area.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self._build_sidebar(sidebar)
        self._build_canvas(canvas_area)

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        # --- Изображение ---
        ttk.Label(parent, text="Изображение", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Button(parent, text="Загрузить изображение...", command=self.on_load_image).pack(fill="x", pady=4)
        self.preview_label = ttk.Label(parent, text="Изображение не загружено", anchor="center")
        self.preview_label.pack(fill="x", pady=4)

        ttk.Separator(parent).pack(fill="x", pady=8)

        # --- Размер листа --- (совпадает с Sidebar.tsx: min=50, без max)
        ttk.Label(parent, text="Размер листа, мм", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        size_row = ttk.Frame(parent)
        size_row.pack(fill="x", pady=4)

        self.board_width = tk.DoubleVar(value=600)
        self.board_height = tk.DoubleVar(value=400)

        ttk.Label(size_row, text="Ширина").grid(row=0, column=0, sticky="w")
        w_entry = ttk.Entry(size_row, textvariable=self.board_width, width=8)
        w_entry.grid(row=0, column=1, padx=4)
        w_entry.bind("<Return>", lambda _e: self.on_board_size_changed())
        w_entry.bind("<FocusOut>", lambda _e: self.on_board_size_changed())

        ttk.Label(size_row, text="Длина").grid(row=0, column=2, sticky="w")
        h_entry = ttk.Entry(size_row, textvariable=self.board_height, width=8)
        h_entry.grid(row=0, column=3, padx=4)
        h_entry.bind("<Return>", lambda _e: self.on_board_size_changed())
        h_entry.bind("<FocusOut>", lambda _e: self.on_board_size_changed())

        ttk.Button(size_row, text="↻", width=3, command=self.swap_board_size).grid(row=0, column=4, padx=4)

        ttk.Separator(parent).pack(fill="x", pady=8)

        # --- Форма отверстий ---
        ttk.Label(parent, text="Форма отверстий", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.shape_var = tk.StringVar(value=DEFAULT_SETTINGS.shape)
        shape_row = ttk.Frame(parent)
        shape_row.pack(fill="x", pady=4)
        for shape_id, label in [("circle", "Круг"), ("square", "Квадрат"), ("hexagon", "Шестигр.")]:
            ttk.Radiobutton(
                shape_row, text=label, value=shape_id, variable=self.shape_var,
                command=self.on_settings_changed,
            ).pack(side="left", padx=4)

        self.stagger_var = tk.BooleanVar(value=DEFAULT_SETTINGS.stagger)
        ttk.Checkbutton(
            parent, text="Шахматный порядок", variable=self.stagger_var,
            command=self.on_settings_changed,
        ).pack(anchor="w", pady=4)

        self.invert_var = tk.BooleanVar(value=DEFAULT_SETTINGS.invert)
        ttk.Checkbutton(
            parent, text="Инверсия яркости", variable=self.invert_var,
            command=self.on_settings_changed,
        ).pack(anchor="w", pady=4)

        ttk.Separator(parent).pack(fill="x", pady=8)

        # --- Параметры перфорации ---
        # Диапазоны/шаги 1:1 с Sidebar.tsx:
        #   spacing: 3..25 step 0.5
        #   minHole: 0.5..(maxHole-0.5) step 0.1
        #   maxHole: (minHole+0.5)..20 step 0.1
        #   sensitivity: 0.3..2.5 step 0.05
        #   threshold: 0..maxHole step 0.1
        ttk.Label(parent, text="Параметры перфорации", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.spacing_f = SliderField(
            parent, "Шаг сетки", 3, 25, 0.5, DEFAULT_SETTINGS.spacing, "мм",
            on_change=self.on_settings_changed,
        )
        self.min_hole_f = SliderField(
            parent, "Мин. отверстие", 0.5, DEFAULT_SETTINGS.max_hole - 0.5, 0.1,
            DEFAULT_SETTINGS.min_hole, "мм", on_change=self.on_min_hole_changed,
        )
        self.max_hole_f = SliderField(
            parent, "Макс. отверстие", DEFAULT_SETTINGS.min_hole + 0.5, 20, 0.1,
            DEFAULT_SETTINGS.max_hole, "мм", on_change=self.on_max_hole_changed,
        )
        self.sensitivity_f = SliderField(
            parent, "Чувствительность", 0.3, 2.5, 0.05, DEFAULT_SETTINGS.sensitivity, "γ",
            on_change=self.on_settings_changed,
        )
        self.threshold_f = SliderField(
            parent, "Порог отсечения", 0, DEFAULT_SETTINGS.max_hole, 0.1,
            DEFAULT_SETTINGS.threshold, "мм", on_change=self.on_settings_changed,
        )

        ttk.Separator(parent).pack(fill="x", pady=8)

        # --- Настройки G-code --- (диапазоны 1:1 с Sidebar.tsx)
        ttk.Label(parent, text="Настройки G-code", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.feed_rate_f = SliderField(
            parent, "Подача XY", 10, 5000, 10, DEFAULT_GCODE.feed_rate, "мм/мин",
            on_change=self.on_gcode_changed,
        )
        self.plunge_rate_f = SliderField(
            parent, "Врезание Z", 10, 2000, 10, DEFAULT_GCODE.plunge_rate, "мм/мин",
            on_change=self.on_gcode_changed,
        )
        self.safe_z_f = SliderField(
            parent, "Безопасная Z", 1, 50, 0.5, DEFAULT_GCODE.safe_z, "мм",
            on_change=self.on_gcode_changed,
        )
        self.cut_depth_f = SliderField(
            parent, "Глубина реза", -30, -0.1, 0.1, DEFAULT_GCODE.cut_depth, "мм",
            on_change=self.on_gcode_changed,
        )
        self.tool_diameter_f = SliderField(
            parent, "Диаметр фрезы", 0.5, 20, 0.1, DEFAULT_GCODE.tool_diameter, "мм",
            on_change=self.on_gcode_changed,
        )
        self.spindle_speed_f = SliderField(
            parent, "Шпиндель", 1000, 30000, 500, DEFAULT_GCODE.spindle_speed, "RPM",
            on_change=self.on_gcode_changed,
        )

        ttk.Separator(parent).pack(fill="x", pady=8)

        ttk.Button(parent, text="Сбросить настройки", command=self.reset_settings).pack(fill="x", pady=(0, 8))

        ttk.Separator(parent).pack(fill="x", pady=8)

        # --- Экспорт ---
        ttk.Label(parent, text="Экспорт", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Button(parent, text="Экспорт DXF", command=self.export_dxf).pack(fill="x", pady=2)
        ttk.Button(parent, text="Экспорт SVG", command=self.export_svg).pack(fill="x", pady=2)
        ttk.Button(parent, text="Экспорт CSV", command=self.export_csv).pack(fill="x", pady=2)
        ttk.Button(parent, text="Экспорт G-code", command=self.export_gcode).pack(fill="x", pady=2)

        self.stats_label = ttk.Label(parent, text="", foreground="#555", justify="left")
        self.stats_label.pack(anchor="w", pady=8)

    def _build_canvas(self, parent: ttk.Frame) -> None:
        self.canvas = tk.Canvas(parent, bg="#0a0f17", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.draw())

    # ------------------------------------------------------------------
    # Логика
    # ------------------------------------------------------------------
    def current_settings(self) -> PerfoSettings:
        return PerfoSettings(
            spacing=self.spacing_f.get(),
            min_hole=self.min_hole_f.get(),
            max_hole=self.max_hole_f.get(),
            sensitivity=max(0.01, self.sensitivity_f.get()),
            invert=self.invert_var.get(),
            threshold=self.threshold_f.get(),
            shape=self.shape_var.get(),
            stagger=self.stagger_var.get(),
        )

    def current_gcode_settings(self) -> GCodeSettings:
        return GCodeSettings(
            feed_rate=self.feed_rate_f.get(),
            plunge_rate=self.plunge_rate_f.get(),
            safe_z=self.safe_z_f.get(),
            cut_depth=self.cut_depth_f.get(),
            tool_diameter=self.tool_diameter_f.get(),
            spindle_speed=self.spindle_speed_f.get(),
        )

    def on_load_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp")],
        )
        if not path:
            return
        try:
            self.image = Image.open(path)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть изображение:\n{e}")
            return

        thumb = self.image.copy()
        thumb.thumbnail((280, 160))
        thumb_gray = thumb.convert("L").convert("RGB")
        self._thumb_photo = ImageTk.PhotoImage(thumb_gray)
        self.preview_label.configure(image=self._thumb_photo, text="")

        self.recalculate()

    def on_settings_changed(self) -> None:
        self.recalculate()

    def on_min_hole_changed(self) -> None:
        # Как на сайте: min_hole не может быть больше max_hole - 0.5,
        # а max_hole не может быть меньше min_hole + 0.5.
        self.max_hole_f.set_range(self.min_hole_f.get() + 0.5, 20)
        self.threshold_f.set_range(0, self.max_hole_f.get())
        self.recalculate()

    def on_max_hole_changed(self) -> None:
        self.min_hole_f.set_range(0.5, self.max_hole_f.get() - 0.5)
        self.threshold_f.set_range(0, self.max_hole_f.get())
        self.recalculate()

    def on_gcode_changed(self) -> None:
        pass  # G-code параметры применяются только при экспорте

    def on_board_size_changed(self) -> None:
        try:
            w = max(50, float(self.board_width.get()))
            h = max(50, float(self.board_height.get()))
        except (tk.TclError, ValueError):
            return
        self.board_width.set(w)
        self.board_height.set(h)
        self.recalculate()

    def swap_board_size(self) -> None:
        w, h = self.board_width.get(), self.board_height.get()
        self.board_width.set(h)
        self.board_height.set(w)
        self.recalculate()

    def reset_settings(self) -> None:
        """Возвращает все параметры (перфорация, G-code, размер листа)
        к значениям по умолчанию — как DEFAULT_SETTINGS/DEFAULT_GCODE на сайте."""
        # Сначала расширяем диапазоны min/max отверстия, чтобы установка
        # значений по умолчанию не была обрезана текущими лимитами.
        self.min_hole_f.set_range(0.5, 20)
        self.max_hole_f.set_range(0.5, 20)

        self.spacing_f.set(DEFAULT_SETTINGS.spacing)
        self.min_hole_f.set(DEFAULT_SETTINGS.min_hole)
        self.max_hole_f.set(DEFAULT_SETTINGS.max_hole)
        self.sensitivity_f.set(DEFAULT_SETTINGS.sensitivity)
        self.threshold_f.set(DEFAULT_SETTINGS.threshold)

        # Восстанавливаем связанные диапазоны (как при обычном изменении полей)
        self.max_hole_f.set_range(self.min_hole_f.get() + 0.5, 20)
        self.min_hole_f.set_range(0.5, self.max_hole_f.get() - 0.5)
        self.threshold_f.set_range(0, self.max_hole_f.get())

        self.shape_var.set(DEFAULT_SETTINGS.shape)
        self.stagger_var.set(DEFAULT_SETTINGS.stagger)
        self.invert_var.set(DEFAULT_SETTINGS.invert)

        self.feed_rate_f.set(DEFAULT_GCODE.feed_rate)
        self.plunge_rate_f.set(DEFAULT_GCODE.plunge_rate)
        self.safe_z_f.set(DEFAULT_GCODE.safe_z)
        self.cut_depth_f.set(DEFAULT_GCODE.cut_depth)
        self.tool_diameter_f.set(DEFAULT_GCODE.tool_diameter)
        self.spindle_speed_f.set(DEFAULT_GCODE.spindle_speed)

        self.board_width.set(600)
        self.board_height.set(400)

        self.recalculate()

    def recalculate(self) -> None:
        if self.image is None:
            return
        settings = self.current_settings()
        try:
            self.result = generate_perforation(
                self.image, settings, self.board_width.get(), self.board_height.get()
            )
        except Exception as e:
            messagebox.showerror("Ошибка расчёта", str(e))
            return
        self.draw()
        self.stats_label.configure(
            text=(
                f"Сетка: {self.result.cols}×{self.result.rows}\n"
                f"Отверстий: {len(self.result.holes)}\n"
                f"Лист: {self.result.width_mm}×{self.result.height_mm} мм"
            )
        )

    def draw(self) -> None:
        self.canvas.delete("all")
        if self.result is None:
            self.canvas.create_text(
                300, 200, text="Загрузите изображение,\nчтобы увидеть перфорацию",
                fill="#7a8a99", font=("Segoe UI", 14), justify="center",
            )
            return

        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        margin = 20
        scale = min(
            (cw - margin * 2) / self.result.width_mm,
            (ch - margin * 2) / self.result.height_mm,
        )
        scale = max(scale, 0.01)

        ox, oy = margin, margin

        # рамка листа
        self.canvas.create_rectangle(
            ox, oy, ox + self.result.width_mm * scale, oy + self.result.height_mm * scale,
            outline="#f99e37", width=2,
        )

        # отверстия
        for hole in self.result.holes:
            cx, cy = ox + hole.x * scale, oy + hole.y * scale
            r = (hole.d / 2) * scale
            if self.result.shape == "circle":
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#2dd4bf", outline="")
            else:
                verts = shape_vertices(self.result.shape, hole.x, hole.y, hole.d)
                flat = []
                for vx, vy in verts:
                    flat.append(ox + vx * scale)
                    flat.append(oy + vy * scale)
                self.canvas.create_polygon(flat, fill="#2dd4bf", outline="")

    # ------------------------------------------------------------------
    # Экспорт
    # ------------------------------------------------------------------
    def _require_result(self) -> bool:
        if self.result is None or not self.result.holes:
            messagebox.showwarning("Нет данных", "Сначала загрузите изображение.")
            return False
        return True

    def _save(self, default_name: str, ext: str, content: str, filetypes) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=ext, initialfile=default_name, filetypes=filetypes,
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        messagebox.showinfo("Готово", f"Файл сохранён:\n{path}")

    def export_dxf(self) -> None:
        if not self._require_result():
            return
        self._save("perforation.dxf", ".dxf", to_dxf(self.result), [("DXF файл", "*.dxf")])

    def export_svg(self) -> None:
        if not self._require_result():
            return
        self._save("perforation.svg", ".svg", to_svg(self.result), [("SVG файл", "*.svg")])

    def export_csv(self) -> None:
        if not self._require_result():
            return
        self._save("perforation.csv", ".csv", to_csv(self.result), [("CSV файл", "*.csv")])

    def export_gcode(self) -> None:
        if not self._require_result():
            return
        self._save(
            "perforation.nc", ".nc", to_gcode(self.result, self.current_gcode_settings()),
            [("G-code файл", "*.nc")],
        )


def main() -> None:
    root = tk.Tk()
    try:
        style = ttk.Style()
        style.theme_use("clam")
    except tk.TclError:
        pass
    app = PerfoStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()