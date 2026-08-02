import Icon from '@/components/ui/icon';
import { Button } from '@/components/ui/button';
import { PerfoResult } from '@/lib/perfo';

interface HeaderProps {
  canUndo: boolean;
  canRedo: boolean;
  undo: () => void;
  redo: () => void;
  result: PerfoResult | null;
  exportSVG: () => void;
  exportPDF: () => void;
  exportCSV: () => void;
  exportGCode: () => void;
  exportDXF: () => void;
}

const Header = ({
  canUndo,
  canRedo,
  undo,
  redo,
  result,
  exportSVG,
  exportPDF,
  exportCSV,
  exportGCode,
  exportDXF,
}: HeaderProps) => {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-primary/15 border border-primary/40 flex items-center justify-center animate-glow">
          <Icon name="Grid3x3" className="text-primary" size={20} />
        </div>
        <div>
          <h1 className="font-bold text-lg leading-none tracking-tight">
            Perfo<span className="text-primary">Studio</span>
          </h1>
          <p className="text-[11px] text-muted-foreground font-mono">image → vector DXF</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={undo} disabled={!canUndo} title="Отменить">
          <Icon name="Undo2" size={18} />
        </Button>
        <Button variant="ghost" size="icon" onClick={redo} disabled={!canRedo} title="Повторить">
          <Icon name="Redo2" size={18} />
        </Button>
        <div className="w-px h-6 bg-border mx-1" />
        <Button onClick={exportSVG} variant="secondary" disabled={!result} className="gap-2">
          <Icon name="FileImage" size={16} /> SVG
        </Button>
        <Button onClick={exportPDF} variant="secondary" disabled={!result} className="gap-2">
          <Icon name="Printer" size={16} /> PDF 1:1
        </Button>
        <Button onClick={exportCSV} variant="secondary" disabled={!result} className="gap-2">
          <Icon name="Table2" size={16} /> CSV
        </Button>
        <Button onClick={exportGCode} variant="secondary" disabled={!result} className="gap-2">
          <Icon name="Terminal" size={16} /> G-code
        </Button>
        <Button onClick={exportDXF} disabled={!result} className="gap-2 font-semibold">
          <Icon name="Download" size={16} /> Экспорт DXF
        </Button>
      </div>
    </header>
  );
};

export default Header;
