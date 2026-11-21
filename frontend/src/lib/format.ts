// Turkish number/date formatting used everywhere in the UI.

const DATE_TIME = new Intl.DateTimeFormat("tr-TR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const TIME = new Intl.DateTimeFormat("tr-TR", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

const NUMBER = new Intl.NumberFormat("tr-TR");

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return DATE_TIME.format(date);
}

export function formatTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return TIME.format(date);
}

export function formatNumber(value?: number | null): string {
  if (value === undefined || value === null) return "—";
  return NUMBER.format(value);
}

export function formatBytes(bytes?: number | null): string {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toLocaleString("tr-TR", { maximumFractionDigits: 1 })} ${units[unit]}`;
}

/** "1 dk 24 sn" style duration, from milliseconds. */
export function formatDuration(ms?: number | null): string {
  if (ms === undefined || ms === null || ms < 0) return "—";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds} sn`;
  return `${minutes} dk ${seconds.toString().padStart(2, "0")} sn`;
}

export function elapsedBetween(
  from?: string | null,
  to?: string | null,
): number | null {
  if (!from) return null;
  const start = new Date(from).getTime();
  const end = to ? new Date(to).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end)) return null;
  return end - start;
}
