"use client";

import { useEffect, useRef } from "react";
import { Play } from "lucide-react";
import { formatTime } from "@/lib/format";

type Props = {
  src: string | null;
  currentTime: number;
  durationSec: number;
  onTime: (sec: number) => void;
};

export function VideoPanel({ src, currentTime, durationSec, onTime }: Props) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (Math.abs(el.currentTime - currentTime) > 0.35) {
      el.currentTime = currentTime;
    }
  }, [currentTime]);

  return (
    <div className="relative aspect-video overflow-hidden rounded-2xl bg-[#111]">
      {!src && (
        <div
          className="pointer-events-none absolute inset-0 opacity-50"
          style={{
            background:
              "radial-gradient(120% 80% at 20% 20%, #3b82f6 0%, transparent 50%), radial-gradient(80% 80% at 80% 80%, #f97316 0%, transparent 45%)",
          }}
        />
      )}
      {src ? (
        <video
          ref={ref}
          src={src}
          className="h-full w-full object-cover"
          controls
          onTimeUpdate={(e) => onTime(e.currentTarget.currentTime)}
        />
      ) : (
        <button
          type="button"
          className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 text-white"
          onClick={() => onTime(currentTime)}
        >
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white/15 backdrop-blur-sm">
            <Play className="ml-0.5 h-6 w-6 fill-white" />
          </span>
          <span className="text-[13px] text-white/70">
            {formatTime(currentTime)} / {formatTime(durationSec)}
          </span>
          <span className="text-[12px] text-white/40">
            Sample video · click a dip to seek
          </span>
        </button>
      )}
    </div>
  );
}
