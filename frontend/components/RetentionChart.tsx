"use client";

import { useMemo, useRef, useState } from "react";
import { formatTime, parseTimestamp } from "@/lib/format";
import type { CurvePoint, Dip } from "@/lib/types";

type Props = {
  curve: CurvePoint[];
  durationSec: number;
  dips: Dip[];
  currentTime: number;
  onSeek: (sec: number) => void;
};

const W = 640;
const H = 240;
const PAD = { l: 40, r: 16, t: 20, b: 32 };
const INNER_W = W - PAD.l - PAD.r;
const INNER_H = H - PAD.t - PAD.b;
const Y_MAX = 130;

export function RetentionChart({
  curve,
  durationSec,
  dips,
  currentTime,
  onSeek,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<{ t: number; pct: number } | null>(null);

  const xOf = (t: number) => PAD.l + (t / Math.max(durationSec, 1)) * INNER_W;
  const yOf = (pct: number) => PAD.t + (1 - pct / Y_MAX) * INNER_H;

  const { path, area } = useMemo(() => {
    const x = (t: number) => PAD.l + (t / Math.max(durationSec, 1)) * INNER_W;
    const y = (pct: number) => PAD.t + (1 - pct / Y_MAX) * INNER_H;
    if (curve.length === 0) return { path: "", area: "" };
    const pts = curve.map((p) => ({ x: x(p.t), y: y(p.pct) }));
    let d = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i === 0 ? 0 : i - 1];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[i + 2] ?? p2;
      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;
      d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
    }
    const last = curve[curve.length - 1];
    const first = curve[0];
    return {
      path: d,
      area: `${d} L ${x(last.t)} ${y(0)} L ${x(first.t)} ${y(0)} Z`,
    };
  }, [curve, durationSec]);

  function timeFromClientX(clientX: number): number {
    const svg = svgRef.current;
    if (!svg) return 0;
    const rect = svg.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * W;
    const t = ((x - PAD.l) / INNER_W) * durationSec;
    return Math.min(durationSec, Math.max(0, t));
  }

  function pctAt(t: number): number {
    if (curve.length === 0) return 0;
    if (t <= curve[0].t) return curve[0].pct;
    for (let i = 1; i < curve.length; i++) {
      if (t <= curve[i].t) {
        const a = curve[i - 1];
        const b = curve[i];
        const u = (t - a.t) / Math.max(0.001, b.t - a.t);
        return a.pct + (b.pct - a.pct) * u;
      }
    }
    return curve[curve.length - 1].pct;
  }

  const yTicks = [0, 50, 100, 120];
  const xTicks = [0, 10, 20, durationSec].filter((t, i, arr) => arr.indexOf(t) === i);

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-[220px] w-full cursor-crosshair select-none"
        onMouseMove={(e) => {
          const t = timeFromClientX(e.clientX);
          setHover({ t, pct: pctAt(t) });
        }}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => onSeek(timeFromClientX(e.clientX))}
        role="img"
        aria-label="Audience retention curve"
      >
        {yTicks.map((tick) => (
          <g key={tick}>
            <line
              x1={PAD.l}
              x2={W - PAD.r}
              y1={yOf(tick)}
              y2={yOf(tick)}
              stroke={tick === 100 ? "#d4d4d8" : "#f4f4f5"}
              strokeDasharray={tick === 100 ? "4 4" : undefined}
            />
            <text
              x={PAD.l - 8}
              y={yOf(tick) + 4}
              textAnchor="end"
              fontSize="11"
              fill="#a1a1aa"
            >
              {tick}%
            </text>
          </g>
        ))}
        {xTicks.map((tick) => (
          <text
            key={tick}
            x={xOf(tick)}
            y={H - 10}
            textAnchor="middle"
            fontSize="11"
            fill="#a1a1aa"
          >
            {formatTime(tick)}
          </text>
        ))}
        <path d={area} fill="rgba(43,127,255,0.08)" />
        <path
          d={path}
          fill="none"
          stroke="#2b7fff"
          strokeWidth="2.25"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <line
          x1={xOf(currentTime)}
          x2={xOf(currentTime)}
          y1={PAD.t}
          y2={H - PAD.b}
          stroke="#111"
          strokeOpacity="0.35"
          strokeWidth="1.25"
        />
        {dips.map((dip) => {
          const t = parseTimestamp(dip.t);
          const pct = pctAt(t);
          return (
            <g
              key={dip.t}
              onClick={(e) => {
                e.stopPropagation();
                onSeek(t);
              }}
              className="cursor-pointer"
            >
              <circle cx={xOf(t)} cy={yOf(pct)} r="7" fill="#fff" />
              <circle cx={xOf(t)} cy={yOf(pct)} r="4.5" fill="#dc2626" />
            </g>
          );
        })}
      </svg>
      {hover && (
        <div className="pointer-events-none absolute top-1 right-2 rounded-md border border-line bg-white px-2 py-1 text-[12px] text-[#444] shadow-sm">
          {formatTime(hover.t)} · {Math.round(hover.pct)}%
        </div>
      )}
    </div>
  );
}
