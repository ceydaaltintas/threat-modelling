"use client";

import { levelClasses, levelForScore } from "@/lib/levels";
import { cn } from "@/lib/utils";

const SCALE = [1, 2, 3, 4, 5];

/**
 * The 5x5 likelihood x impact grid.
 *
 * One component, used by the analysis step and the dashboard: the two used
 * to be separate copies of the same markup, and when the axis labels were
 * fixed in one the other kept drifting.
 */
export function RiskHeatmap({
  heatmap,
  thresholds,
  size = "md",
}: {
  heatmap: Record<string, number> | null | undefined;
  thresholds: { low: number; medium: number; high: number };
  size?: "sm" | "md";
}) {
  const max = Math.max(1, ...Object.values(heatmap ?? {}));
  const cell = size === "sm" ? "h-8" : "h-9";

  return (
    <div className="flex gap-1.5">
      {/* Row labels share the grid's row height and gap, and must not
          stretch: as a flex child this column grew to cover the x axis
          labels too, which pushed every label below its own row. */}
      <div className={cn("grid gap-1 self-start text-[10px] text-muted-foreground")}>
        {[...SCALE].reverse().map((value) => (
          <span
            key={value}
            className={cn("flex items-center justify-end pr-0.5", cell)}
          >
            {value}
          </span>
        ))}
      </div>
      <div className="flex-1">
        <div className="grid grid-cols-5 gap-1">
          {[...SCALE].reverse().map((impact) =>
            SCALE.map((likelihood) => {
              const count = heatmap?.[`${likelihood}x${impact}`] ?? 0;
              const level = levelForScore(impact * likelihood, thresholds);
              return (
                <div
                  key={`${impact}-${likelihood}`}
                  title={`Olasılık ${likelihood} × Etki ${impact} = ${
                    impact * likelihood
                  } (${level}) · ${count} tehdit`}
                  className={cn(
                    "flex items-center justify-center rounded border text-[11px] font-medium",
                    cell,
                    levelClasses[level],
                    count === 0 && "opacity-30",
                  )}
                  style={
                    count > 0
                      ? { opacity: 0.5 + (count / max) * 0.5 }
                      : undefined
                  }
                >
                  {count || ""}
                </div>
              );
            }),
          )}
        </div>
        <div className="mt-1 grid grid-cols-5 gap-1 text-center text-[10px] text-muted-foreground">
          {SCALE.map((value) => (
            <span key={value}>{value}</span>
          ))}
        </div>
        <p className="mt-0.5 text-center text-[10px] text-muted-foreground">
          Yatay: olasılık · Dikey: etki
        </p>
      </div>
    </div>
  );
}
