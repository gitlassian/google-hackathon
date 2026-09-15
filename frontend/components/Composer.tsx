"use client";

import { useRef, useState } from "react";
import {
  ArrowUp,
  ChevronDown,
  Image as ImageIcon,
  Mic,
  Plus,
  X,
  Clapperboard,
} from "lucide-react";
import { cn } from "@/lib/format";

type Props = {
  placeholder: string;
  disabled?: boolean;
  sending?: boolean;
  videoName: string | null;
  screenshotName: string | null;
  screenshotPreview: string | null;
  suggestions?: string[];
  footerLeft: string;
  contextLabel: string;
  onSend: (text: string) => void;
  onAttachVideo: (file: File) => void;
  onAttachScreenshot: (file: File) => void;
  onRemoveVideo: () => void;
  onRemoveScreenshot: () => void;
  onSuggestion?: (text: string) => void;
};

export function Composer({
  placeholder,
  disabled,
  sending,
  videoName,
  screenshotName,
  screenshotPreview,
  suggestions,
  footerLeft,
  contextLabel,
  onSend,
  onAttachVideo,
  onAttachScreenshot,
  onRemoveVideo,
  onRemoveScreenshot,
  onSuggestion,
}: Props) {
  const [text, setText] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  const videoInput = useRef<HTMLInputElement>(null);
  const shotInput = useRef<HTMLInputElement>(null);
  const canSend = !disabled && !sending && (text.trim().length > 0 || !!videoName || !!screenshotName);

  function submit() {
    if (!canSend) return;
    onSend(text.trim());
    setText("");
  }

  return (
    <div className="relative z-10 bg-white px-4 pt-3 pb-3">
      <div className="pointer-events-none absolute inset-x-0 -top-8 h-8 bg-gradient-to-b from-transparent to-white" />
      {suggestions && suggestions.length > 0 && (
        <div className="mx-auto mb-2 flex max-w-[760px] gap-1.5 overflow-x-auto [scrollbar-width:none]">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onSuggestion?.(s)}
              className="shrink-0 rounded-full border border-line bg-white px-3 py-1 text-[12.5px] text-[#444] hover:bg-[#f7f7f8]"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="composer-shadow relative mx-auto max-w-[760px] rounded-[22px] border border-[#e8e8e8] bg-white">
        {(videoName || screenshotName) && (
          <div className="flex flex-wrap gap-2 px-3.5 pt-3">
            {videoName && (
              <Chip
                icon={<Clapperboard className="h-3.5 w-3.5" />}
                label={videoName}
                onRemove={onRemoveVideo}
              />
            )}
            {screenshotName && (
              <Chip
                icon={
                  screenshotPreview ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={screenshotPreview}
                      alt=""
                      className="h-4 w-4 rounded-[3px] object-cover"
                    />
                  ) : (
                    <ImageIcon className="h-3.5 w-3.5" />
                  )
                }
                label={screenshotName}
                onRemove={onRemoveScreenshot}
              />
            )}
          </div>
        )}

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder={placeholder}
          rows={2}
          className="block w-full resize-none bg-transparent px-4 pt-3.5 pb-1 text-[15px] leading-6 text-[#111] placeholder:text-[#b0b0b4]"
        />

        <div className="flex items-center justify-between px-2.5 pb-2.5 pt-1">
          <div className="relative">
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="flex h-8 w-8 items-center justify-center rounded-full text-[#555] hover:bg-[#f4f4f5]"
              aria-label="Add files"
            >
              <Plus className="h-[18px] w-[18px]" />
            </button>
            {menuOpen && (
              <div className="absolute bottom-[42px] left-0 z-20 w-52 overflow-hidden rounded-xl border border-line bg-white py-1 shadow-lg">
                <MenuItem
                  label="Upload video"
                  onClick={() => {
                    setMenuOpen(false);
                    videoInput.current?.click();
                  }}
                />
                <MenuItem
                  label="Upload retention screenshot"
                  onClick={() => {
                    setMenuOpen(false);
                    shotInput.current?.click();
                  }}
                />
              </div>
            )}
          </div>

          <div className="flex items-center gap-1">
            <div className="relative">
              <button
                type="button"
                onClick={() => setModelOpen((v) => !v)}
                className="flex items-center gap-1 rounded-lg px-2 py-1 text-[13px] text-[#555] hover:bg-[#f4f4f5]"
              >
                Gemini 3.8 Flash
                <ChevronDown className="h-3.5 w-3.5" />
              </button>
              {modelOpen && (
                <div className="absolute right-0 bottom-[42px] z-20 w-56 overflow-hidden rounded-xl border border-line bg-white py-1 shadow-lg">
                  <div className="px-3 py-2 text-[13px] text-[#111]">
                    Gemini 3.8 Flash
                    <div className="text-[11px] text-muted">Static video · recommended</div>
                  </div>
                  <div className="px-3 py-2 text-[13px] text-[#999]">
                    Gemini 3.1 Pro
                    <div className="text-[11px] text-muted">Fallback</div>
                  </div>
                </div>
              )}
            </div>
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-full text-[#888] hover:bg-[#f4f4f5]"
              aria-label="Voice input"
            >
              <Mic className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={submit}
              disabled={!canSend}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full",
                canSend
                  ? "bg-accent text-white hover:bg-[#1b6ff2]"
                  : "bg-[#ececee] text-[#b0b0b4]",
              )}
              aria-label="Send"
            >
              <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
            </button>
          </div>
        </div>

        <input
          ref={videoInput}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onAttachVideo(file);
            e.target.value = "";
          }}
        />
        <input
          ref={shotInput}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onAttachScreenshot(file);
            e.target.value = "";
          }}
        />
      </div>

      <div className="mx-auto mt-1.5 flex max-w-[760px] items-center justify-between px-1 text-[12px] text-muted">
        <span>{footerLeft}</span>
        <span>{contextLabel}</span>
      </div>
    </div>
  );
}

function Chip({
  icon,
  label,
  onRemove,
}: {
  icon: React.ReactNode;
  label: string;
  onRemove: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-[#fafafa] py-1 pr-1 pl-1.5 text-[12px] text-[#333]">
      {icon}
      <span className="max-w-[160px] truncate">{label}</span>
      <button
        type="button"
        onClick={onRemove}
        className="rounded p-0.5 hover:bg-[#eee]"
        aria-label={`Remove ${label}`}
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

function MenuItem({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="block w-full px-3 py-2 text-left text-[13px] text-[#222] hover:bg-[#f6f6f7]"
    >
      {label}
    </button>
  );
}
