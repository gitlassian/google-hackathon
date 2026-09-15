export function ScoreRing({
  score,
  size = 72,
}: {
  score: number;
  size?: number;
}) {
  const r = 28;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.min(100, Math.max(0, score)) / 100) * c;
  const color =
    score >= 70 ? "#16a34a" : score >= 50 ? "#d97706" : "#dc2626";

  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      aria-label={`Score ${score} out of 100`}
    >
      <svg viewBox="0 0 72 72" className="h-full w-full -rotate-90">
        <circle
          cx="36"
          cy="36"
          r={r}
          fill="none"
          stroke="#efefef"
          strokeWidth="6"
        />
        <circle
          cx="36"
          cy="36"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div
        className="absolute inset-0 flex items-center justify-center text-[22px] font-semibold tracking-tight"
        style={{ color }}
      >
        {score}
      </div>
    </div>
  );
}
