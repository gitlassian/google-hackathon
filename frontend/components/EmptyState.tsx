"use client";

import { useRef, useState } from "react";
import { Clapperboard, Image as ImageIcon } from "lucide-react";
import { cn, isYouTubeUrl } from "@/lib/format";

type Props = {
  youtubeUrl: string;
  videoName: string | null;
  screenshotName: string | null;
  screenshotPreview: string | null;
  onUrl: (url: string) => void;
  onVideo: (file: File) => void;
  onScreenshot: (file: File) => void;
  onSample: () => void;
  error?: string | null;
};

export function EmptyState({
  youtubeUrl,
  videoName,
  screenshotName,
  screenshotPreview,
  onUrl,
  onVideo,
  onScreenshot,
  onSample,
  error,
}: Props) {
  return (
    <article className="mx-auto w-full max-w-[720px] px-6 pt-10 pb-16">
      <h2 className="text-[28px] leading-[1.2] font-semibold tracking-tight text-[#111]">
        New analysis
      </h2>
      <p className="mt-3 max-w-[560px] text-[16px] leading-7 text-[#444]">
        Drop a Short and a YouTube Studio retention screenshot. Coach watches
        the video, reads the curve, and tells you what to change next time.
      </p>
      {error && (
        <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[14px] text-red-700">
          {error}
        </p>
      )}

      <div className="mt-8 grid gap-3 md:grid-cols-2">
        <DropZone
          title="Short"
          hint="YouTube link or video file"
          accent={!!videoName || !!youtubeUrl}
          accept="video/*"
          onFile={onVideo}
        >
          <Clapperboard className="h-5 w-5 text-[#8e8e93]" />
          <p className="mt-3 text-[13px] text-[#555]">
            {videoName ? videoName : "Drop an mp4, or paste a public Shorts URL"}
          </p>
          <input
            value={youtubeUrl}
            onChange={(e) => onUrl(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            placeholder="https://youtube.com/shorts/…"
            className={cn(
              "relative z-10 mt-3 w-full rounded-lg border bg-white px-3 py-2 text-[13px] text-[#111] placeholder:text-[#b0b0b4]",
              youtubeUrl && !isYouTubeUrl(youtubeUrl)
                ? "border-[#f1c0c0]"
                : "border-line",
            )}
          />
        </DropZone>

        <DropZone
          title="Retention screenshot"
          hint="YouTube Studio → Audience"
          accent={!!screenshotName}
          accept="image/*"
          onFile={onScreenshot}
        >
          {screenshotPreview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={screenshotPreview}
              alt="Retention screenshot preview"
              className="mb-2 h-16 w-full rounded-md object-cover"
            />
          ) : (
            <ImageIcon className="h-5 w-5 text-[#8e8e93]" />
          )}
          <p className="mt-3 text-[13px] text-[#555]">
            {screenshotName
              ? screenshotName
              : "Required for dip diagnosis. PNG or JPEG from Studio."}
          </p>
        </DropZone>
      </div>

      <div className="mt-8">
        <button
          type="button"
          onClick={onSample}
          className="text-[14px] font-medium text-accent hover:underline"
        >
          Try a sample analysis
        </button>
        <span className="text-[14px] text-muted">
          {" "}
          — no files needed, mock report.
        </span>
      </div>
    </article>
  );
}

function DropZone({
  title,
  hint,
  accent,
  accept,
  onFile,
  children,
}: {
  title: string;
  hint: string;
  accent: boolean;
  accept: string;
  onFile: (file: File) => void;
  children: React.ReactNode;
}) {
  const [over, setOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      className={cn(
        "rounded-2xl border border-dashed p-5",
        accent
          ? "border-[#c9d9f8] bg-[#f7faff]"
          : over
            ? "border-[#cfcfd2] bg-[#fafafa]"
            : "border-[#e4e4e7] bg-white",
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file) onFile(file);
      }}
    >
      <div className="mb-1 text-[13px] font-medium text-[#111]">{title}</div>
      <div className="text-[12px] text-muted">{hint}</div>
      <div
        className="mt-4"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        role="presentation"
      >
        {children}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
