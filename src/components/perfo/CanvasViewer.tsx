import { RefObject } from 'react';
import Icon from '@/components/ui/icon';
import { Button } from '@/components/ui/button';
import { PerfoResult } from '@/lib/perfo';
import { Stat } from '@/components/perfo/shared';

interface CanvasViewerProps {
  canvasRef: RefObject<HTMLCanvasElement>;
  viewportRef: RefObject<HTMLDivElement>;
  result: PerfoResult | null;
  zoom: number;
  setZoom: React.Dispatch<React.SetStateAction<number>>;
  fitWidth: () => void;
  fitHeight: () => void;
  showGcodePath: boolean;
  setShowGcodePath: React.Dispatch<React.SetStateAction<boolean>>;
}

const CanvasViewer = ({
  canvasRef,
  viewportRef,
  result,
  zoom,
  setZoom,
  fitWidth,
  fitHeight,
  showGcodePath,
  setShowGcodePath,
}: CanvasViewerProps) => {
  return (
    <main className="perfo-canvas relative flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-card/30 backdrop-blur-sm">
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => setZoom((z) => Math.max(0.1, Math.round((z - 0.25) * 100) / 100))}>
            <Icon name="ZoomOut" size={18} />
          </Button>
          <span className="font-mono text-sm w-14 text-center">{Math.round(zoom * 100)}%</span>
          <Button variant="ghost" size="icon" onClick={() => setZoom((z) => Math.min(8, Math.round((z + 0.25) * 100) / 100))}>
            <Icon name="ZoomIn" size={18} />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setZoom(1)} title="100%">
            <Icon name="Maximize" size={18} />
          </Button>

          <div className="w-px h-5 bg-border mx-1" />

          {/* Масштабирование по ширине */}
          <Button
            variant="ghost"
            size="sm"
            disabled={!result}
            onClick={fitWidth}
            title="Вписать по ширине"
            className="gap-1.5 text-xs text-muted-foreground hover:text-primary px-2"
          >
            <Icon name="ArrowLeftRight" size={14} />
            По ширине
          </Button>

          {/* Масштабирование по высоте */}
          <Button
            variant="ghost"
            size="sm"
            disabled={!result}
            onClick={fitHeight}
            title="Вписать по высоте"
            className="gap-1.5 text-xs text-muted-foreground hover:text-primary px-2"
          >
            <Icon name="ArrowUpDown" size={14} />
            По длине
          </Button>

          <div className="w-px h-5 bg-border mx-1" />

          {/* Предпросмотр G-code */}
          <Button
            variant="ghost"
            size="sm"
            disabled={!result}
            onClick={() => setShowGcodePath((v) => !v)}
            className={`gap-1.5 text-xs px-2 transition-all ${
              showGcodePath
                ? 'text-amber-400 bg-amber-400/10 hover:bg-amber-400/15'
                : 'text-muted-foreground hover:text-amber-400'
            }`}
            title="Показать траекторию G-code"
          >
            <Icon name="Route" size={14} />
            Траектория ЧПУ
          </Button>
        </div>
        {result && (
          <div className="flex items-center gap-4 font-mono text-xs text-muted-foreground">
            <Stat icon="Grid3x3" value={`${result.cols}×${result.rows}`} />
            <Stat icon="Circle" value={`${result.holes.length} отв.`} />
            <Stat icon="Ruler" value={`${result.widthMm}×${result.heightMm} мм`} />
          </div>
        )}
      </div>

      {/* Canvas */}
      <div ref={viewportRef} className="flex-1 overflow-auto p-8 flex items-center justify-center">
        {result ? (
          <canvas
            ref={canvasRef}
            className="rounded-lg shadow-2xl shadow-primary/10 animate-scale-in max-w-none"
            style={{ imageRendering: 'auto' }}
          />
        ) : (
          <div className="text-center text-muted-foreground animate-fade-in">
            <Icon name="ScanLine" size={56} className="mx-auto mb-4 text-primary/40" />
            <p className="text-lg font-medium">Загрузите изображение</p>
            <p className="text-sm mt-1">и перфорация сгенерируется автоматически</p>
          </div>
        )}
      </div>
    </main>
  );
};

export default CanvasViewer;
