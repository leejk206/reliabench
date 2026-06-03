export function pct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export function pctValue(rate: number): number {
  return Math.round(rate * 1000) / 10; // 0..100 with 1 decimal
}

export function ms(value: number): string {
  return `${Math.round(value)} ms`;
}

export function passRateAccent(rate: number): "green" | "amber" | "red" {
  if (rate >= 0.8) return "green";
  if (rate >= 0.6) return "amber";
  return "red";
}

export function fmtTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export function truncate(text: string, max = 120): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + "…";
}
