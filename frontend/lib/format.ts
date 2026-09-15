export function formatTime(sec: number): string {
  const clamped = Math.max(0, Math.floor(sec));
  const m = Math.floor(clamped / 60);
  const s = clamped % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function parseTimestamp(t: string): number {
  const parts = t.split(":").map((p) => Number(p));
  if (parts.length === 2 && parts.every((n) => Number.isFinite(n))) {
    return parts[0] * 60 + parts[1];
  }
  return 0;
}

export function isYouTubeUrl(value: string): boolean {
  return /youtu\.be\/|youtube\.com\/(watch|shorts|live|embed)/i.test(value.trim());
}

export function uid(): string {
  return Math.random().toString(36).slice(2, 9);
}

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function ratingLabel(rating: "strong" | "ok" | "weak"): string {
  if (rating === "strong") return "Strong";
  if (rating === "ok") return "OK";
  return "Weak";
}
