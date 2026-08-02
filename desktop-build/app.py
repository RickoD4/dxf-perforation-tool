"""
PerfoStudio Desktop — генератор перфорации из изображения (offline-версия).

Полный перенос логики веб-приложения PerfoStudio на Python + tkinter:
    - загрузка изображения (PNG/JPG/BMP)
    - настройка шага сетки, диаметров отверстий, чувствительности,
      порога отсечения, формы (круг/квадрат/шестиугольник), шахматного
      порядка и инверсии яркости
    - живой предпросмотр перфорации на canvas
    - экспорт в DXF, SVG, CSV и G-code

Сборка в .exe: python build.py app.py PerfoStudio
(или просто дважды кликните СОБРАТЬ.bat)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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


class PerfoStudioApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PerfoStudio — image → vector DXF")
        self.root.geometry("1200x760")
        self.root.minsize(900, 600)

        self.image: Image.Image | None = None
        self.settings = PerfoSettings(**vars(DEFAULT_SETTINGS))
        self.gcode_settings = GCodeSettings(**vars(DEFAULT_GCODE))
        self.board_width = tk.DoubleVar(value=600)
        self.board_height = tk.DoubleVar(value=400)
        self.result = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        sidebar = ttk.Frame(container, width=320)
        sidebar.pack(side="left", fill="y", padx=8, pady=8)
        sidebar.pack_propagate(False)

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

        # --- Размер листа ---
        ttk.Label(parent, text="Размер листа, мм", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        size_row = ttk.Frame(parent)
        size_row.pack(fill="x", pady=4)
        ttk.Label(size_row, text="Ширина").grid(row=0, column=0, sticky="w")
        ttk.Entry(size_row, textvariable=self.board_width, width=8).grid(row=0, column=1, padx=4)
        ttk.Label(size_row, text="Длина").grid(row=0, column=2, sticky="w")
        ttk.Entry(size_row, textvariable=self.board_height, width=8).grid(row=0, column=3, padx=4)
        ttk.Button(size_row, text="↻", width=3, command=self.swap_board_size).grid(row=0, column=4, padx=4)

        ttk.Separator(parent).pack(fill="x", pady=8)

        # --- Форма отверстий ---
        ttk.Label(parent, text="Форма отверстий", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.shape_var = tk.StringVar(value=self.settings.shape)
        shape_row = ttk.Frame(parent)
        shape_row.pack(fill="x", pady=4)
        for shape_id, label in [("circle", "Круг"), ("square", "Квадрат"), ("hexagon", "Шестигр.")]:
            ttk.Radiobutton(
                shape_row, text=label, value=shape_id, variable=self.shape_var,
                command=self.on_settings_changed,
            ).pack(side="left", padx=4)

        self.stagger_var = tk.BooleanVar(value=self.settings.stagger)
        ttk.Checkbutton(
            parent, text="Шахматный порядок", variable=self.stagger_var,
            command=self.on_settings_changed,
        ).pack(anchor="w", pady=4)

        self.invert_var = tk.BooleanVar(value=self.settings.invert)
        ttk.Checkbutton(
            parent, text="Инверсия яркости", variable=self.invert_var,
            command=self.on_settings_changed,
        ).pack(anchor="w", pady=4)

        ttk.Separator(parent).pack(fill="x", pady=8)

        # --- Параметры перфорации (слайдеры) ---
        ttk.Label(parent, text="Параметры перфорации", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.spacing_var = self._slider(parent, "Шаг сетки, мм", 3, 25, self.settings.spacing)
        self.min_hole_var = self._slider(parent, "Мин. отверстие, мм", 0.5, 19, self.settings.min_hole)
        self.max_hole_var = self._slider(parent, "Макс. отверстие, мм", 1, 20, self.settings.max_hole)
        self.sensitivity_var = self._slider(parent, "Чувствительность (γ)", 0.3, 2.5, self.settings.sensitivity)
        self.threshold_var = self._slider(parent, "Порог отсечения, мм", 0, 20, self.settings.threshold)

        ttk.Separator(parent).pack(fill="x", pady=8)

        # --- Экспорт ---
        ttk.Label(parent, text="Экспорт", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Button(parent, text="Экспорт DXF", command=self.export_dxf).pack(fill="x", pady=2)
        ttk.Button(parent, text="Экспорт SVG", command=self.export_svg).pack(fill="x", pady=2)
        ttk.Button(parent, text="Экспорт CSV", command=self.export_csv).pack(fill="x", pady=2)
        ttk.Button(parent, text="Экспорт G-code", command=self.export_gcode).pack(fill="x", pady=2)

        self.stats_label = ttk.Label(parent, text="", foreground="#555")
        self.stats_label.pack(anchor="w", pady=8)

    def _slider(self, parent: ttk.Frame, label: str, lo: float, hi: float, value: float) -> tk.DoubleVar:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label).pack(anchor="w")
        var = tk.DoubleVar(value=value)
        scale = ttk.Scale(
            row, from_=lo, to=hi, orient="horizontal", variable=var,
            command=lambda _v: self.on_settings_changed(),
        )
        scale.pack(fill="x")
        return var

    def _build_canvas(self, parent: ttk.Frame) -> None:
        self.canvas = tk.Canvas(parent, bg="#0a0f17", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.draw())

    # ------------------------------------------------------------------
    # Логика
    # ------------------------------------------------------------------
    def current_settings(self) -> PerfoSettings:
        return PerfoSettings(
            spacing=self.spacing_var.get(),
            min_hole=min(self.min_hole_var.get(), self.max_hole_var.get() - 0.1),
            max_hole=self.max_hole_var.get(),
            sensitivity=max(0.01, self.sensitivity_var.get()),
            invert=self.invert_var.get(),
            threshold=self.threshold_var.get(),
            shape=self.shape_var.get(),
            stagger=self.stagger_var.get(),
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

    def swap_board_size(self) -> None:
        w, h = self.board_width.get(), self.board_height.get()
        self.board_width.set(h)
        self.board_height.set(w)
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
            "perforation.nc", ".nc", to_gcode(self.result, self.gcode_settings),
            [("G-code файл", "*.nc")],
        )


def main() -> None:
    root = tk.Tk()
    app = PerfoStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()