"""
Логика генерации перфорации — прямой перенос алгоритма из веб-версии
PerfoStudio (src/lib/perfo.ts) на Python, без изменений в математике.

Содержит:
    - PerfoSettings / GCodeSettings — настройки (дата-классы)
    - Hole / PerfoResult — результат генерации
    - shape_vertices — вершины фигуры отверстия (квадрат/шестиугольник)
    - generate_perforation — основной алгоритм (гистограммное выравнивание
      + гамма-коррекция + защита от наложения отверстий)
    - to_dxf / to_svg / to_csv / to_gcode — экспорт в те же форматы,
      что и веб-версия
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple

from PIL import Image

HoleShape = str  # 'circle' | 'square' | 'hexagon'


@dataclass
class PerfoSettings:
    spacing: float = 8.0       # шаг сетки, мм
    min_hole: float = 1.5      # минимальный диаметр отверстия, мм
    max_hole: float = 6.0      # максимальный диаметр отверстия, мм
    sensitivity: float = 1.0   # чувствительность 0..2 (гамма-коррекция)
    invert: bool = False       # светлое = большие отверстия или наоборот
    threshold: float = 1.0     # порог отсечения мелких отверстий, мм
    shape: HoleShape = "circle"
    stagger: bool = False      # шахматное расположение


DEFAULT_SETTINGS = PerfoSettings()


@dataclass
class GCodeSettings:
    feed_rate: float = 1000.0     # подача XY, мм/мин
    plunge_rate: float = 300.0    # подача по Z (врезание), мм/мин
    safe_z: float = 5.0           # безопасная высота Z, мм
    cut_depth: float = -3.0       # глубина фрезерования, мм
    tool_diameter: float = 3.0    # диаметр инструмента, мм
    spindle_speed: float = 12000.0  # обороты шпинделя, RPM


DEFAULT_GCODE = GCodeSettings()


@dataclass
class Hole:
    x: float  # мм
    y: float  # мм
    d: float  # диаметр (описанной окружности), мм


@dataclass
class PerfoResult:
    holes: List[Hole] = field(default_factory=list)
    width_mm: int = 0
    height_mm: int = 0
    cols: int = 0
    rows: int = 0
    shape: HoleShape = "circle"


def shape_vertices(shape: HoleShape, cx: float, cy: float, d: float) -> List[Tuple[float, float]]:
    """Вершины многоугольника отверстия в мм-координатах
    (центр cx,cy; d — диаметр описанной окружности)."""
    r = d / 2
    if shape == "square":
        s = r * 0.886  # приравниваем площадь к кругу примерно
        return [
            (cx - s, cy - s),
            (cx + s, cy - s),
            (cx + s, cy + s),
            (cx - s, cy + s),
        ]
    # hexagon (плоской стороной вверх)
    pts: List[Tuple[float, float]] = []
    for i in range(6):
        a = math.radians(60 * i + 30)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def generate_perforation(
    image: Image.Image,
    s: PerfoSettings,
    board_width_mm: float = 600.0,
    board_height_mm: float = 400.0,
) -> PerfoResult:
    """Реальная генерация перфорации по яркости пикселей изображения.
    Алгоритм: нормализация гистограммы — реальный диапазон яркостей
    растягивается на весь диапазон min..max отверстий для максимальной чёткости."""

    cols = max(2, int(board_width_mm // s.spacing))
    rows = max(2, int(board_height_mm // s.spacing))

    # Уменьшаем изображение до размера сетки (аналог рендера в canvas)
    small = image.convert("RGB").resize((cols, rows), Image.LANCZOS)
    pixels = list(small.getdata())

    total = cols * rows

    # Шаг 1: собираем все значения яркости
    lums = [(0.299 * r + 0.587 * g + 0.114 * b) / 255 for r, g, b in pixels]

    # Шаг 2: гистограммное выравнивание (histogram equalization)
    # Строим отсортированный массив и находим ранг каждого пикселя в [0..1]
    sorted_lums = sorted(lums)
    denom = (total - 1) if total > 1 else 1
    equalized = [bisect.bisect_left(sorted_lums, lum) / denom for lum in lums]

    # Максимально допустимый диаметр — чтобы отверстия не касались соседних.
    # Минимальное расстояние между любыми соседними центрами всегда равно
    # s.spacing (см. комментарий в оригинальном perfo.ts).
    max_safe = s.spacing - 0.1
    d_max = min(s.max_hole, max_safe)
    d_min = min(s.min_hole, d_max)

    # Шаг 3: дополнительная гамма-коррекция поверх выравнивания
    holes: List[Hole] = []
    for r in range(rows):
        offset = s.spacing / 2 if (s.stagger and r % 2 == 1) else 0
        for c in range(cols):
            n = r * cols + c
            v = equalized[n] if s.invert else 1 - equalized[n]
            v = max(0.0, min(1.0, v)) ** (1 / s.sensitivity)
            d = d_min + v * (d_max - d_min)
            if d < s.threshold:
                continue
            x = c * s.spacing + s.spacing / 2 + offset
            if x > board_width_mm:
                continue
            # Округление "как в JS" (Math.round — половина всегда вверх),
            # а не банковское округление round() из Python.
            d_rounded = math.floor(d * 100 + 0.5) / 100
            holes.append(Hole(x=x, y=r * s.spacing + s.spacing / 2, d=d_rounded))

    return PerfoResult(
        holes=holes,
        width_mm=math.floor(board_width_mm + 0.5),
        height_mm=math.floor(board_height_mm + 0.5),
        cols=cols,
        rows=rows,
        shape=s.shape,
    )


def to_dxf(result: PerfoResult) -> str:
    """Генерация настоящего DXF-файла."""
    def h(g: int, v) -> str:
        return f"{g}\n{v}\n"

    body = h(0, "SECTION") + h(2, "ENTITIES")
    for hole in result.holes:
        if result.shape == "circle":
            body += h(0, "CIRCLE")
            body += h(8, "PERFORATION")
            body += h(10, f"{hole.x:.3f}")
            body += h(20, f"{result.height_mm - hole.y:.3f}")
            body += h(30, "0.0")
            body += h(40, f"{hole.d / 2:.3f}")
        else:
            verts = shape_vertices(result.shape, hole.x, result.height_mm - hole.y, hole.d)
            body += h(0, "LWPOLYLINE")
            body += h(8, "PERFORATION")
            body += h(90, len(verts))
            body += h(70, 1)  # замкнутая
            for vx, vy in verts:
                body += h(10, f"{vx:.3f}")
                body += h(20, f"{vy:.3f}")
    body += h(0, "ENDSEC") + h(0, "EOF")
    return body


def to_svg(result: PerfoResult) -> str:
    """Генерация SVG для просмотра / экспорта."""
    shapes = []
    for hole in result.holes:
        if result.shape == "circle":
            shapes.append(f'<circle cx="{hole.x}" cy="{hole.y}" r="{hole.d / 2:.2f}"/>')
        else:
            pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in shape_vertices(result.shape, hole.x, hole.y, hole.d))
            shapes.append(f'<polygon points="{pts}"/>')
    shapes_str = "".join(shapes)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{result.width_mm}mm" '
        f'height="{result.height_mm}mm" viewBox="0 0 {result.width_mm} {result.height_mm}">'
        f'<rect width="100%" height="100%" fill="none"/><g fill="black">{shapes_str}</g></svg>'
    )


def to_csv(result: PerfoResult) -> str:
    """Экспорт в CSV для ЧПУ-станков.
    Колонки: №, X (мм), Y (мм), Диаметр (мм), Радиус (мм), Форма"""
    lines = [
        "# PerfoStudio — координаты отверстий",
        f"# Лист: {result.width_mm} x {result.height_mm} мм | "
        f"Отверстий: {len(result.holes)} | Форма: {result.shape}",
        "N;X_mm;Y_mm;Diameter_mm;Radius_mm;Shape",
    ]
    for i, hole in enumerate(result.holes):
        lines.append(
            f"{i + 1};{hole.x:.3f};{hole.y:.3f};{hole.d:.3f};{hole.d / 2:.3f};{result.shape}"
        )
    return "\r\n".join(lines)


def to_pdf(result: PerfoResult, path: str) -> None:
    """Экспорт в PDF с реальным масштабом 1:1 в мм (векторный, как печать
    SVG 1:1 в веб-версии). Использует reportlab: страница ровно
    width_mm x height_mm, координаты переведены из мм в points (1мм = 72/25.4 pt)."""
    from reportlab.lib.units import mm as MM
    from reportlab.pdfgen import canvas as pdf_canvas

    c = pdf_canvas.Canvas(path, pagesize=(result.width_mm * MM, result.height_mm * MM))
    c.setFillColorRGB(0, 0, 0)
    for hole in result.holes:
        # PDF-координаты начинаются снизу-слева, а y перфорации — сверху-вниз.
        py = (result.height_mm - hole.y) * MM
        px = hole.x * MM
        if result.shape == "circle":
            r = (hole.d / 2) * MM
            c.circle(px, py, r, stroke=0, fill=1)
        else:
            verts = shape_vertices(result.shape, hole.x, result.height_mm - hole.y, hole.d)
            p = c.beginPath()
            for i, (vx, vy) in enumerate(verts):
                if i == 0:
                    p.moveTo(vx * MM, vy * MM)
                else:
                    p.lineTo(vx * MM, vy * MM)
            p.close()
            c.drawPath(p, stroke=0, fill=1)
    c.showPage()
    c.save()


def to_gcode(result: PerfoResult, g: GCodeSettings) -> str:
    """G-code для фрезерного ЧПУ.
    Каждое отверстие: подход → врезание → круговая фреза (G2) → подъём."""
    lines: List[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines += [
        "; PerfoStudio — G-code export",
        f"; Date: {now}",
        f"; Sheet: {result.width_mm} x {result.height_mm} mm",
        f"; Holes: {len(result.holes)} | Shape: {result.shape}",
        f"; Tool diameter: {g.tool_diameter} mm",
        f"; Cut depth: {g.cut_depth} mm | Feed: {g.feed_rate} mm/min",
        "",
        "G21        ; мм",
        "G90        ; абсолютные координаты",
        "G17        ; плоскость XY",
        f"M3 S{g.spindle_speed:.0f} ; шпиндель ВКЛ",
        "G4 P2      ; пауза 2 сек",
        f"G0 Z{g.safe_z:.3f} ; безопасная высота",
        "",
    ]

    for i, hole in enumerate(result.holes):
        r = max(0.01, (hole.d - g.tool_diameter) / 2)  # радиус траектории
        start_x = f"{hole.x + r:.3f}"
        cy = f"{hole.y:.3f}"
        cx = f"{hole.x:.3f}"

        lines.append(f"; Отверстие #{i + 1}  D={hole.d}мм  X={cx} Y={cy}")
        lines.append(f"G0 X{start_x} Y{cy}")
        lines.append(f"G1 Z{g.cut_depth:.3f} F{g.plunge_rate} ; врезание")
        if r > 0.01:
            lines.append(f"G2 X{start_x} Y{cy} I{-r:.3f} J0.000 F{g.feed_rate} ; круговая фреза")
        lines.append(f"G0 Z{g.safe_z:.3f}")
        lines.append("")

    lines += [
        f"G0 Z{g.safe_z:.3f}",
        "G0 X0 Y0   ; парковка",
        "M5         ; шпиндель ВЫКЛ",
        "M30        ; конец программы",
    ]

    return "\r\n".join(lines)