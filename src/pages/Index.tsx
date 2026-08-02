import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  DEFAULT_SETTINGS,
  DEFAULT_GCODE,
  GCodeSettings,
  PerfoSettings,
  PerfoResult,
  generatePerforation,
  shapeVertices,
  toDXF,
  toSVG,
  toPDF,
  toCSV,
  toGCode,
  download,
} from '@/lib/perfo';
import Header from '@/components/perfo/Header';
import Sidebar from '@/components/perfo/Sidebar';
import CanvasViewer from '@/components/perfo/CanvasViewer';

const Index = () => {
  const [img, setImg] = useState<HTMLImageElement | null>(null);
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [settings, setSettings] = useState<PerfoSettings>(DEFAULT_SETTINGS);
  const [boardWidth, setBoardWidth] = useState(600);
  const [boardHeight, setBoardHeight] = useState(400);
  const [gcodeSettings, setGcodeSettings] = useState<GCodeSettings>(DEFAULT_GCODE);
  const [showGcodePath, setShowGcodePath] = useState(false);
  const [result, setResult] = useState<PerfoResult | null>(null);
  const [zoom, setZoom] = useState(1);

  const [history, setHistory] = useState<PerfoSettings[]>([DEFAULT_SETTINGS]);
  const [hIndex, setHIndex] = useState(0);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);

  const pushHistory = (next: PerfoSettings) => {
    const trimmed = history.slice(0, hIndex + 1);
    const upd = [...trimmed, next];
    setHistory(upd);
    setHIndex(upd.length - 1);
  };

  const update = (patch: Partial<PerfoSettings>) => {
    const next = { ...settings, ...patch };
    setSettings(next);
    pushHistory(next);
  };

  const undo = () => {
    if (hIndex > 0) {
      const i = hIndex - 1;
      setHIndex(i);
      setSettings(history[i]);
    }
  };
  const redo = () => {
    if (hIndex < history.length - 1) {
      const i = hIndex + 1;
      setHIndex(i);
      setSettings(history[i]);
    }
  };

  const [isGrayscale, setIsGrayscale] = useState(false);

  const loadImage = (src: string, grayscale: boolean) => {
    const image = new Image();
    image.onload = () => {
      if (!grayscale) {
        setImg(image);
        setImgSrc(src);
        return;
      }
      // Конвертация в ч/б через canvas
      const cv = document.createElement('canvas');
      cv.width = image.width;
      cv.height = image.height;
      const ctx = cv.getContext('2d')!;
      ctx.drawImage(image, 0, 0);
      const imageData = ctx.getImageData(0, 0, cv.width, cv.height);
      const d = imageData.data;
      for (let i = 0; i < d.length; i += 4) {
        const lum = Math.round(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
        d[i] = d[i + 1] = d[i + 2] = lum;
      }
      ctx.putImageData(imageData, 0, 0);
      const bwSrc = cv.toDataURL('image/png');
      const bwImg = new Image();
      bwImg.onload = () => {
        setImg(bwImg);
        setImgSrc(bwSrc);
      };
      bwImg.src = bwSrc;
    };
    image.src = src;
  };

  const onFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const src = e.target?.result as string;
      setIsGrayscale(false);
      loadImage(src, false);
      toast.success('Изображение загружено');
    };
    reader.readAsDataURL(file);
  };

  // Сохраняем оригинальный src отдельно для конвертации
  const [originalSrc, setOriginalSrc] = useState<string | null>(null);

  const convertToGrayscale = () => {
    if (!imgSrc) return;
    const src = originalSrc ?? imgSrc;
    setOriginalSrc(src);
    setIsGrayscale(true);
    loadImage(src, true);
    toast.success('Изображение переведено в Ч/Б');
  };

  const revertToColor = () => {
    if (!originalSrc) return;
    setIsGrayscale(false);
    loadImage(originalSrc, false);
    setOriginalSrc(null);
    toast.success('Восстановлено цветное изображение');
  };

  // Пересчёт перфорации
  useEffect(() => {
    if (!img) return;
    const res = generatePerforation(img, settings, boardWidth, boardHeight);
    setResult(res);
  }, [img, settings, boardWidth, boardHeight]);

  // Отрисовка
  const draw = useCallback(() => {
    const cv = canvasRef.current;
    if (!cv || !result) return;
    const ctx = cv.getContext('2d')!;
    const scale = (2 * zoom);
    cv.width = result.widthMm * scale;
    cv.height = result.heightMm * scale;

    ctx.fillStyle = '#0a0f17';
    ctx.fillRect(0, 0, cv.width, cv.height);

    // сетка
    ctx.strokeStyle = 'rgba(45,212,191,0.08)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= result.widthMm; x += settings.spacing) {
      ctx.beginPath();
      ctx.moveTo(x * scale, 0);
      ctx.lineTo(x * scale, cv.height);
      ctx.stroke();
    }
    for (let y = 0; y <= result.heightMm; y += settings.spacing) {
      ctx.beginPath();
      ctx.moveTo(0, y * scale);
      ctx.lineTo(cv.width, y * scale);
      ctx.stroke();
    }

    // отверстия
    ctx.fillStyle = '#2dd4bf';
    for (const h of result.holes) {
      ctx.beginPath();
      if (result.shape === 'circle') {
        ctx.arc(h.x * scale, h.y * scale, (h.d / 2) * scale, 0, Math.PI * 2);
      } else {
        const verts = shapeVertices(result.shape, h.x, h.y, h.d);
        verts.forEach(([vx, vy], i) => {
          if (i === 0) ctx.moveTo(vx * scale, vy * scale);
          else ctx.lineTo(vx * scale, vy * scale);
        });
        ctx.closePath();
      }
      ctx.fill();
    }

    // рамка листа
    ctx.strokeStyle = 'rgba(249,158,55,0.6)';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, cv.width, cv.height);

    // G-code траектория
    if (showGcodePath && result.holes.length > 0) {
      const toolR = Math.max(0.01, (gcodeSettings.toolDiameter) / 2);

      // линии перемещения (G0 — быстрый ход)
      ctx.strokeStyle = 'rgba(251,191,36,0.55)';
      ctx.lineWidth = Math.max(1, scale * 0.15);
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(0, 0);
      result.holes.forEach((h) => {
        const tR = Math.max(0.01, (h.d - gcodeSettings.toolDiameter) / 2);
        const sx = (h.x + tR) * scale;
        const sy = h.y * scale;
        ctx.lineTo(sx, sy);
        ctx.moveTo(sx, sy);
      });
      ctx.stroke();
      ctx.setLineDash([]);

      // траектория фрезы на каждом отверстии (окружность радиуса tR)
      result.holes.forEach((h, i) => {
        const tR = Math.max(0.01, (h.d - gcodeSettings.toolDiameter) / 2);

        // окружность траектории
        ctx.beginPath();
        ctx.arc(h.x * scale, h.y * scale, tR * scale, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(251,146,60,0.75)';
        ctx.lineWidth = Math.max(1, scale * 0.2);
        ctx.stroke();

        // диаметр инструмента (пунктир)
        ctx.beginPath();
        ctx.arc(h.x * scale, h.y * scale, toolR * scale, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(251,146,60,0.25)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);

        // номер отверстия (каждые 5)
        if (i % 5 === 0 && scale > 0.8) {
          ctx.fillStyle = 'rgba(251,191,36,0.9)';
          ctx.font = `bold ${Math.max(8, scale * 3)}px JetBrains Mono, monospace`;
          ctx.textAlign = 'center';
          ctx.fillText(`${i + 1}`, h.x * scale, (h.y - h.d / 2 - 1.5) * scale);
        }
      });

      // начало координат — крест
      ctx.strokeStyle = 'rgba(251,191,36,0.9)';
      ctx.lineWidth = 2;
      const cs = Math.max(8, scale * 4);
      ctx.beginPath(); ctx.moveTo(-cs, 0); ctx.lineTo(cs, 0); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, -cs); ctx.lineTo(0, cs); ctx.stroke();
    }
  }, [result, zoom, settings.spacing, showGcodePath, gcodeSettings]);

  useEffect(() => {
    draw();
  }, [draw]);

  const exportDXF = () => {
    if (!result) return;
    download('perforation.dxf', toDXF(result), 'application/dxf');
    toast.success(`Экспортировано ${result.holes.length} отверстий в DXF`);
  };
  const exportSVG = () => {
    if (!result) return;
    download('perforation.svg', toSVG(result), 'image/svg+xml');
    toast.success('Экспортировано в SVG');
  };

  const exportPDF = () => {
    if (!result) return;
    toPDF(result);
    toast.success(`PDF ${result.widthMm}×${result.heightMm} мм, масштаб 1:1`);
  };

  const exportCSV = () => {
    if (!result) return;
    download('perforation.csv', toCSV(result), 'text/csv;charset=utf-8;');
    toast.success(`CSV экспортирован — ${result.holes.length} строк для ЧПУ`);
  };

  const exportGCode = () => {
    if (!result) return;
    download('perforation.nc', toGCode(result, gcodeSettings), 'text/plain');
    toast.success(`G-code экспортирован — ${result.holes.length} отверстий`);
  };

  // Вписать по ширине viewport
  const fitWidth = () => {
    if (!result || !viewportRef.current) return;
    const vw = viewportRef.current.clientWidth - 64;
    const z = vw / (result.widthMm * 2);
    setZoom(Math.max(0.1, Math.round(z * 100) / 100));
  };

  // Вписать по высоте viewport
  const fitHeight = () => {
    if (!result || !viewportRef.current) return;
    const vh = viewportRef.current.clientHeight - 64;
    const z = vh / (result.heightMm * 2);
    setZoom(Math.max(0.1, Math.round(z * 100) / 100));
  };

  // Подогнать размер листа под пропорции изображения
  const fitToImage = () => {
    if (!img) return;
    const aspect = img.height / img.width;
    setBoardHeight(Math.round(boardWidth * aspect));
    toast.success('Длина подогнана под пропорции изображения');
  };

  return (
    <div className="min-h-screen text-foreground">
      <Header
        canUndo={hIndex > 0}
        canRedo={hIndex < history.length - 1}
        undo={undo}
        redo={redo}
        result={result}
        exportSVG={exportSVG}
        exportPDF={exportPDF}
        exportCSV={exportCSV}
        exportGCode={exportGCode}
        exportDXF={exportDXF}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr]">
        <Sidebar
          imgSrc={imgSrc}
          img={img}
          fileRef={fileRef}
          onFile={onFile}
          isGrayscale={isGrayscale}
          convertToGrayscale={convertToGrayscale}
          revertToColor={revertToColor}
          boardWidth={boardWidth}
          boardHeight={boardHeight}
          setBoardWidth={setBoardWidth}
          setBoardHeight={setBoardHeight}
          fitToImage={fitToImage}
          settings={settings}
          update={update}
          gcodeSettings={gcodeSettings}
          setGcodeSettings={setGcodeSettings}
          exportGCode={exportGCode}
          result={result}
        />

        <CanvasViewer
          canvasRef={canvasRef}
          viewportRef={viewportRef}
          result={result}
          zoom={zoom}
          setZoom={setZoom}
          fitWidth={fitWidth}
          fitHeight={fitHeight}
          showGcodePath={showGcodePath}
          setShowGcodePath={setShowGcodePath}
        />
      </div>
    </div>
  );
};

export default Index;
