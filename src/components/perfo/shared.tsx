import Icon from '@/components/ui/icon';
import { Slider } from '@/components/ui/slider';

export const SectionTitle = ({ icon, text }: { icon: string; text: string }) => (
  <div className="flex items-center gap-2 mb-3">
    <Icon name={icon} size={15} className="text-primary" />
    <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{text}</h2>
  </div>
);

export const Field = ({ label, children }: { label: React.ReactNode; children: React.ReactNode }) => (
  <div className="space-y-1.5">
    <label className="text-sm text-muted-foreground flex items-center justify-between">{label}</label>
    {children}
  </div>
);

export const SliderRow = ({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (v: number) => void;
}) => (
  <div className="py-2">
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-mono text-sm text-primary font-semibold">
        {value} <span className="text-muted-foreground text-xs">{unit}</span>
      </span>
    </div>
    <Slider value={[value]} min={min} max={max} step={step} onValueChange={([v]) => onChange(v)} />
  </div>
);

export const Stat = ({ icon, value }: { icon: string; value: string }) => (
  <span className="flex items-center gap-1.5">
    <Icon name={icon} size={13} className="text-primary/70" />
    {value}
  </span>
);
