// Risk level helpers. Colour is never the only signal: every badge also
// carries its Turkish text label.

export type Level = "Kritik" | "Yüksek" | "Orta" | "Düşük";

export const LEVELS: Level[] = ["Kritik", "Yüksek", "Orta", "Düşük"];

export const levelClasses: Record<Level, string> = {
  Kritik: "border-level-critical/40 bg-level-critical/10 text-level-critical",
  Yüksek: "border-level-high/40 bg-level-high/10 text-level-high",
  Orta: "border-level-medium/40 bg-level-medium/10 text-level-medium",
  Düşük: "border-level-low/40 bg-level-low/10 text-level-low",
};

/** score -> level, using the thresholds the backend reports. */
export function levelForScore(
  score: number,
  thresholds: { low: number; medium: number; high: number },
): Level {
  if (score <= thresholds.low) return "Düşük";
  if (score <= thresholds.medium) return "Orta";
  if (score <= thresholds.high) return "Yüksek";
  return "Kritik";
}
