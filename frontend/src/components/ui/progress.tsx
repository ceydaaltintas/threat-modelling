import { cn } from "@/lib/utils";

export function Progress({
  value,
  className,
  label,
}: {
  value: number;
  className?: string;
  label?: string;
}) {
  const clamped = Math.min(100, Math.max(0, Math.round(value * 100)));
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-muted", className)}
    >
      <div
        className="h-full rounded-full bg-accent transition-[width] duration-300"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
