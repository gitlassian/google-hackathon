"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { analyzeShort, chatAboutShort } from "@/lib/api-client";
import {
  emptyAnalysis,
  INITIAL_ANALYSES,
  LOADING_STEPS,
  STREET_FOOD_REPORT,
  suggestionsFor,
} from "@/lib/mock-data";
import { mockReply } from "@/lib/mock-reply";
import { isYouTubeUrl, uid } from "@/lib/format";
import type { Analysis, NavId, Report } from "@/lib/types";
import { Composer } from "./Composer";
import { EmptyState } from "./EmptyState";
import { LoadingState } from "./LoadingState";
import { ReportDocument } from "./ReportDocument";
import { SettingsPanel } from "./SettingsPanel";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell() {
  const [analyses, setAnalyses] = useState<Analysis[]>(INITIAL_ANALYSES);
  const [selectedId, setSelectedId] = useState<string>(INITIAL_ANALYSES[0].id);
  const [nav, setNav] = useState<NavId>("analyses");
  const [mobileOpen, setMobileOpen] = useState(false);
  const attachments = useRef(
    new Map<string, { video?: File; screenshot?: File }>(),
  );

  const selected = useMemo(
    () => analyses.find((a) => a.id === selectedId) ?? null,
    [analyses, selectedId],
  );

  const hasLoading = analyses.some((a) => a.status === "loading");

  useEffect(() => {
    if (!hasLoading) return;
    const handle = window.setInterval(() => {
      setAnalyses((prev) =>
        prev.map((a) => {
          if (a.status !== "loading") return a;
          if (a.loadingStep >= LOADING_STEPS.length - 1) return a;
          return { ...a, loadingStep: a.loadingStep + 1 };
        }),
      );
    }, 2500);
    return () => window.clearInterval(handle);
  }, [hasLoading]);

  function patch(id: string, partial: Partial<Analysis>) {
    setAnalyses((prev) =>
      prev.map((a) => (a.id === id ? { ...a, ...partial } : a)),
    );
  }

  function createNew() {
    const next = emptyAnalysis(uid());
    setAnalyses((prev) => [next, ...prev]);
    setSelectedId(next.id);
    setNav("analyses");
    setMobileOpen(false);
  }

  function setAttachment(
    id: string,
    kind: "video" | "screenshot",
    file: File | undefined,
  ) {
    const current = attachments.current.get(id) ?? {};
    if (kind === "video") current.video = file;
    else current.screenshot = file;
    attachments.current.set(id, current);
  }

  function startAnalysis(id: string, extras: Partial<Analysis> = {}) {
    setAnalyses((prev) =>
      prev.map((a) => {
        if (a.id !== id) return a;
        return {
          ...a,
          status: "loading",
          loadingStep: 0,
          error: null,
          title: a.title === "New analysis" ? "Analyzing…" : a.title,
          ...extras,
        };
      }),
    );
  }

  async function runRemoteAnalysis(id: string, youtubeUrl: string) {
    startAnalysis(id, { youtubeUrl });
    const files = attachments.current.get(id);
    try {
      const result = await analyzeShort({
        youtubeUrl,
        video: files?.video,
        screenshot: files?.screenshot,
      });
      setAnalyses((prev) =>
        prev.map((a) => {
          if (a.id !== id) return a;
          return {
            ...a,
            status: "ready",
            loadingStep: 0,
            error: null,
            report: result.report,
            stats: result.stats,
            interactionId: result.interactionId,
            title: titleFromReport(result.report, a.title),
          };
        }),
      );
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Analyze failed. Check the API key.";
      setAnalyses((prev) =>
        prev.map((a) => {
          if (a.id !== id) return a;
          return {
            ...a,
            status: "draft",
            loadingStep: 0,
            error: message,
            title: a.title === "Analyzing…" ? "New analysis" : a.title,
          };
        }),
      );
    }
  }

  async function handleSend(text: string) {
    if (!selected) return;
    if (selected.status === "ready" && selected.report) {
      const content = text.trim() || "Go on.";
      const user = { id: uid(), role: "user" as const, content };
      patch(selected.id, { messages: [...selected.messages, user] });
      try {
        const reply = selected.interactionId
          ? await chatAboutShort(selected.interactionId, content)
          : {
              reply: mockReply(content, selected.report),
              interactionId: selected.interactionId,
            };
        setAnalyses((prev) =>
          prev.map((a) => {
            if (a.id !== selected.id) return a;
            return {
              ...a,
              interactionId: reply.interactionId ?? a.interactionId,
              messages: [
                ...a.messages,
                { id: uid(), role: "assistant", content: reply.reply },
              ],
            };
          }),
        );
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Chat failed.";
        setAnalyses((prev) =>
          prev.map((a) => {
            if (a.id !== selected.id) return a;
            return {
              ...a,
              messages: [
                ...a.messages,
                { id: uid(), role: "assistant", content: message },
              ],
            };
          }),
        );
      }
      return;
    }

    const url = isYouTubeUrl(text) ? text.trim() : selected.youtubeUrl;
    if (!url && !selected.videoName) {
      if (text.trim()) patch(selected.id, { youtubeUrl: text.trim() });
      return;
    }
    await runRemoteAnalysis(selected.id, url || selected.youtubeUrl);
  }

  function runSample() {
    if (!selected) {
      createNew();
      return;
    }
    startAnalysis(selected.id, {
      youtubeUrl: "https://www.youtube.com/shorts/example-street-food",
      videoName: "street-food.mp4",
      screenshotName: "studio-retention.png",
      title: "Analyzing…",
    });
    window.setTimeout(() => {
      setAnalyses((prev) =>
        prev.map((a) => {
          if (a.id !== selected.id) return a;
          return {
            ...a,
            status: "ready",
            loadingStep: 0,
            report: STREET_FOOD_REPORT,
            interactionId: null,
            title: "Hook dies at 0:03",
          };
        }),
      );
    }, 3600);
  }

  const title =
    nav === "settings" ? "Settings" : (selected?.title ?? "New analysis");

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-white">
      <div className="hidden h-full md:flex">
        <Sidebar
          analyses={analyses}
          selectedId={selectedId}
          nav={nav}
          onSelect={(id) => {
            setSelectedId(id);
            setNav("analyses");
          }}
          onNew={createNew}
          onNav={setNav}
        />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <Sidebar
            analyses={analyses}
            selectedId={selectedId}
            nav={nav}
            onSelect={(id) => {
              setSelectedId(id);
              setNav("analyses");
              setMobileOpen(false);
            }}
            onNew={createNew}
            onNav={(id) => {
              setNav(id);
              setMobileOpen(false);
            }}
          />
          <button
            type="button"
            className="h-full flex-1 bg-black/20"
            aria-label="Close sidebar"
            onClick={() => setMobileOpen(false)}
          />
        </div>
      )}

      <section className="flex min-w-0 flex-1 flex-col">
        <TopBar
          title={title}
          onOpenSidebar={() => setMobileOpen(true)}
        />

        <div className="thin-scroll min-h-0 flex-1 overflow-y-auto">
          {nav === "settings" && <SettingsPanel />}
          {nav === "analyses" && selected?.status === "draft" && (
            <EmptyState
              youtubeUrl={selected.youtubeUrl}
              videoName={selected.videoName}
              screenshotName={selected.screenshotName}
              screenshotPreview={selected.screenshotPreview}
              onUrl={(youtubeUrl) => patch(selected.id, { youtubeUrl, error: null })}
              onVideo={(file) => {
                setAttachment(selected.id, "video", file);
                patch(selected.id, {
                  videoName: file.name,
                  videoPreview: URL.createObjectURL(file),
                  error: null,
                });
              }}
              onScreenshot={(file) => {
                setAttachment(selected.id, "screenshot", file);
                patch(selected.id, {
                  screenshotName: file.name,
                  screenshotPreview: URL.createObjectURL(file),
                  error: null,
                });
              }}
              onSample={runSample}
              error={selected.error}
            />
          )}
          {nav === "analyses" && selected?.status === "loading" && (
            <LoadingState step={selected.loadingStep} />
          )}
          {nav === "analyses" && selected?.status === "ready" && (
            <ReportDocument analysis={selected} />
          )}
        </div>

        {nav === "analyses" && selected && (
          <Composer
            placeholder={
              selected.status === "ready"
                ? "Ask about this Short…"
                : "Paste a Shorts URL or send to analyze"
            }
            videoName={selected.status === "draft" ? selected.videoName : null}
            screenshotName={
              selected.status === "draft" ? selected.screenshotName : null
            }
            screenshotPreview={
              selected.status === "draft" ? selected.screenshotPreview : null
            }
            suggestions={
              selected.status === "ready" && selected.report
                ? suggestionsFor(selected.report)
                : undefined
            }
            footerLeft="Analysis"
            contextLabel={
              selected.status === "ready"
                ? "Context: 8.6K"
                : selected.screenshotName
                  ? "Screenshot attached"
                  : "No files yet"
            }
            sending={selected.status === "loading"}
            onSend={handleSend}
            onAttachVideo={(file) => {
              setAttachment(selected.id, "video", file);
              patch(selected.id, {
                videoName: file.name,
                videoPreview: URL.createObjectURL(file),
                error: null,
              });
            }}
            onAttachScreenshot={(file) => {
              setAttachment(selected.id, "screenshot", file);
              patch(selected.id, {
                screenshotName: file.name,
                screenshotPreview: URL.createObjectURL(file),
                error: null,
              });
            }}
            onRemoveVideo={() => {
              setAttachment(selected.id, "video", undefined);
              patch(selected.id, { videoName: null, videoPreview: null });
            }}
            onRemoveScreenshot={() => {
              setAttachment(selected.id, "screenshot", undefined);
              patch(selected.id, {
                screenshotName: null,
                screenshotPreview: null,
              });
            }}
            onSuggestion={(text) => handleSend(text)}
          />
        )}
      </section>
    </div>
  );
}

function titleFromReport(report: Report, fallback: string): string {
  const first = report.verdict.split(".")[0]?.trim();
  if (!first) return fallback === "Analyzing…" ? "Analysis" : fallback;
  return first.length > 48 ? `${first.slice(0, 46)}…` : first;
}


