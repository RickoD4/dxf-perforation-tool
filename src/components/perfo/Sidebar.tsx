import { RefObject } from 'react';
import Icon from '@/components/ui/icon';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { GCodeSettings, HoleShape, PerfoResult, PerfoSettings } from '@/lib/perfo';
import { Field, SectionTitle, SliderRow } from '@/components/perfo/shared';

interface SidebarProps {
  imgSrc: string | null;
  img: HTMLImageElement | null;
  fileRef: RefObject<HTMLInputElement>;
  onFile: (file: File) => void;
  isGrayscale: boolean;
  convertToGrayscale: () => void;
  revertToColor: () => void;

  boardWidth: number;
  boardHeight: number;
  setBoardWidth: (v: number) => void;
  setBoardHeight: (v: number) => void;
  fitToImage: () => void;

  settings: PerfoSettings;
  update: (patch: Partial<PerfoSettings>) => void;

  gcodeSettings: GCodeSettings;
  setGcodeSettings: React.Dispatch<React.SetStateAction<GCodeSettings>>;
  exportGCode: () => void;
  result: PerfoResult | null;
}

const Sidebar = ({
  imgSrc,
  img,
  fileRef,
  onFile,
  isGrayscale,
  convertToGrayscale,
  revertToColor,
  boardWidth,
  boardHeight,
  setBoardWidth,
  setBoardHeight,
  fitToImage,
  settings,
  update,
  gcodeSettings,
  setGcodeSettings,
  exportGCode,
  result,
}: SidebarProps) => {
  return (
    <aside className="border-r border-border bg-card/40 p-5 space-y-6 max-h-[calc(100vh-61px)] overflow-y-auto">
      {/* Загрузка */}
      <section className="animate-fade-in">
        <SectionTitle icon="ImageUp" text="Изображение" />
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
        />
        <div
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) onFile(f);
          }}
          className="group cursor-pointer rounded-xl border-2 border-dashed border-border hover:border-primary/60 transition-colors p-4 text-center"
        >
          {imgSrc ? (
            <img
              src={imgSrc}
              alt="preview"
              className="w-full h-32 object-contain rounded-md"
              style={{ filter: 'grayscale(1) contrast(1.1)' }}
            />
          ) : (
            <div className="py-6 text-muted-foreground group-hover:text-primary transition-colors">
              <Icon name="ImagePlus" size={28} className="mx-auto mb-2" />
              <p className="text-sm">Перетащите файл или нажмите</p>
              <p className="text-[11px] font-mono mt-1">PNG · JPG · BMP</p>
            </div>
          )}
        </div>

        {/* Кнопки конвертации */}
        {imgSrc && (
          <div className="flex gap-2 mt-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={isGrayscale}
              onClick={convertToGrayscale}
              className="flex-1 gap-1.5 text-xs border border-border hover:border-primary/50 hover:text-primary text-muted-foreground"
            >
              <Icon name="Circle" size={13} /> Ч/Б
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={!isGrayscale}
              onClick={revertToColor}
              className="flex-1 gap-1.5 text-xs border border-border hover:border-primary/50 hover:text-primary text-muted-foreground"
            >
              <Icon name="Palette" size={13} /> Цвет
            </Button>
          </div>
        )}
      </section>

      {/* Размер листа */}
      <section>
        <SectionTitle icon="Ruler" text="Размер листа" />

        {/* Поля + кнопки управления */}
        <div className="flex items-end gap-2">
          <div className="grid grid-cols-2 gap-2 flex-1">
            <Field label="Ширина, мм">
              <Input
                type="number"
                value={boardWidth}
                min={50}
                onChange={(e) => { const v = Number(e.target.value); if (v >= 50) setBoardWidth(v); }}
                className="font-mono"
              />
            </Field>
            <Field label="Длина, мм">
              <Input
                type="number"
                value={boardHeight}
                min={50}
                onChange={(e) => { const v = Number(e.target.value); if (v >= 50) setBoardHeight(v); }}
                className="font-mono"
              />
            </Field>
          </div>

          {/* Повернуть ориентацию */}
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 border border-border hover:border-primary/50 hover:text-primary"
            title="Повернуть ориентацию"
            onClick={() => { setBoardWidth(boardHeight); setBoardHeight(boardWidth); }}
          >
            <Icon name="RefreshCw" size={16} />
          </Button>
        </div>

        {/* Подогнать под изображение */}
        <Button
          variant="ghost"
          size="sm"
          disabled={!img}
          onClick={fitToImage}
          className="mt-2 w-full gap-2 border border-border hover:border-primary/50 hover:text-primary text-muted-foreground text-xs"
        >
          <Icon name="Scan" size={14} /> Подогнать под изображение
        </Button>

        {/* Пресеты */}
        <div className="flex flex-wrap gap-1.5 mt-2.5">
          {[
            { label: 'A4', w: 210, h: 297 },
            { label: 'A3', w: 297, h: 420 },
            { label: 'A2', w: 420, h: 594 },
            { label: 'A1', w: 594, h: 841 },
            { label: 'A0', w: 841, h: 1189 },
            { label: '1000×2000', w: 1000, h: 2000 },
            { label: '1500×3000', w: 1500, h: 3000 },
          ].map((p) => (
            <button
              key={p.label}
              onClick={() => { setBoardWidth(p.w); setBoardHeight(p.h); }}
              className={`text-[11px] font-mono px-2 py-0.5 rounded border transition-all ${
                (boardWidth === p.w && boardHeight === p.h) || (boardWidth === p.h && boardHeight === p.w)
                  ? 'border-primary text-primary bg-primary/10'
                  : 'border-border text-muted-foreground hover:border-primary/50 hover:text-foreground'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </section>

      {/* Форма отверстий */}
      <section>
        <SectionTitle icon="Shapes" text="Форма отверстий" />
        <div className="grid grid-cols-3 gap-2">
          {([
            { id: 'circle', label: 'Круг', icon: 'Circle' },
            { id: 'square', label: 'Квадрат', icon: 'Square' },
            { id: 'hexagon', label: 'Шестигр.', icon: 'Hexagon' },
          ] as { id: HoleShape; label: string; icon: string }[]).map((sh) => {
            const active = settings.shape === sh.id;
            return (
              <button
                key={sh.id}
                onClick={() => update({ shape: sh.id })}
                className={`flex flex-col items-center gap-1.5 rounded-lg border py-3 transition-all ${
                  active
                    ? 'border-primary bg-primary/15 text-primary shadow-[0_0_14px_hsl(var(--primary)/0.3)]'
                    : 'border-border text-muted-foreground hover:border-primary/50 hover:text-foreground'
                }`}
              >
                <Icon name={sh.icon} size={20} />
                <span className="text-[11px] font-medium">{sh.label}</span>
              </button>
            );
          })}
        </div>
        <div className="flex items-center justify-between py-3 mt-1">
          <span className="text-sm text-muted-foreground flex items-center gap-2">
            <Icon name="LayoutGrid" size={14} className="text-primary" /> Шахматный порядок
          </span>
          <Switch checked={settings.stagger} onCheckedChange={(v) => update({ stagger: v })} />
        </div>
      </section>

      {/* Параметры */}
      <section>
        <SectionTitle icon="SlidersHorizontal" text="Параметры перфорации" />
        <SliderRow
          label="Шаг сетки"
          value={settings.spacing}
          min={3}
          max={25}
          step={0.5}
          unit="мм"
          onChange={(v) => update({ spacing: v })}
        />
        <SliderRow
          label="Мин. отверстие"
          value={settings.minHole}
          min={0.5}
          max={settings.maxHole - 0.5}
          step={0.1}
          unit="мм"
          onChange={(v) => update({ minHole: v })}
        />
        <SliderRow
          label="Макс. отверстие"
          value={settings.maxHole}
          min={settings.minHole + 0.5}
          max={20}
          step={0.1}
          unit="мм"
          onChange={(v) => update({ maxHole: v })}
        />
        <SliderRow
          label="Чувствительность"
          value={settings.sensitivity}
          min={0.3}
          max={2.5}
          step={0.05}
          unit="γ"
          onChange={(v) => update({ sensitivity: v })}
        />
        <SliderRow
          label="Порог отсечения"
          value={settings.threshold}
          min={0}
          max={settings.maxHole}
          step={0.1}
          unit="мм"
          onChange={(v) => update({ threshold: v })}
        />
        <div className="flex items-center justify-between py-2">
          <span className="text-sm text-muted-foreground">Инверсия яркости</span>
          <Switch checked={settings.invert} onCheckedChange={(v) => update({ invert: v })} />
        </div>
      </section>

      {/* G-code настройки */}
      <section>
        <SectionTitle icon="Terminal" text="Настройки G-code" />
        <div className="grid grid-cols-2 gap-2">
          {(
            [
              { label: 'Подача XY, мм/мин', key: 'feedRate', min: 10, max: 5000, step: 10 },
              { label: 'Врезание Z, мм/мин', key: 'plungeRate', min: 10, max: 2000, step: 10 },
              { label: 'Безопасная Z, мм', key: 'safeZ', min: 1, max: 50, step: 0.5 },
              { label: 'Глубина реза, мм', key: 'cutDepth', min: -30, max: -0.1, step: 0.1 },
              { label: 'Диаметр фрезы, мм', key: 'toolDiameter', min: 0.5, max: 20, step: 0.1 },
              { label: 'Шпиндель, RPM', key: 'spindleSpeed', min: 1000, max: 30000, step: 500 },
            ] as { label: string; key: keyof GCodeSettings; min: number; max: number; step: number }[]
          ).map(({ label, key, min, max, step }) => (
            <Field key={key} label={label}>
              <Input
                type="number"
                value={gcodeSettings[key]}
                min={min}
                max={max}
                step={step}
                onChange={(e) => setGcodeSettings((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                className="font-mono text-sm"
              />
            </Field>
          ))}
        </div>
        <Button
          onClick={exportGCode}
          disabled={!result}
          className="w-full mt-3 gap-2"
        >
          <Icon name="Terminal" size={15} /> Экспорт G-code (.nc)
        </Button>
      </section>
    </aside>
  );
};

export default Sidebar;