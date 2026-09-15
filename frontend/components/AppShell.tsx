"use client";

import { useEffect, useMemo, useState } from "react";
import {
  emptyAnalysis,
  INITIAL_ANALYSES,
  LOADING_STEPS,
  STREET_FOOD_REPORT,
  suggestionsFor,
} from "@/lib/mock-data";
import { mockReply } from "@/lib/mock-reply";
import { isYouTubeUrl, uid } from "@/lib/format";
import type { Analysis, NavId } from "@/lib/types";
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
          if (a.loadingStep < LOADING_STEPS.length - 1) {
            return { ...a, loadingStep: a.loadingStep + 1 };
          }
          const report = a.report ?? STREET_FOOD_REPORT;
          return {
            ...a,
            status: "ready",
            loadingStep: 0,
            report,
            title:
              a.title === "Analyzing…" || a.title === "New analysis"
                ? "Hook dies at 0:03"
                : a.title,
          };
        }),
      );
    }, 900);
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

  function startAnalysis(id: string, extras: Partial<Analysis> = {}) {
    setAnalyses((prev) =>
      prev.map((a) => {
        if (a.id !== id) return a;
        return {
          ...a,
          status: "loading",
          loadingStep: 0,
          title: a.title === "New analysis" ? "Analyzing…" : a.title,
          ...extras,
        };
      }),
    );
  }

  function handleSend(text: string) {
    if (!selected) return;
    if (selected.status === "ready" && selected.report) {
      const user = { id: uid(), role: "user" as const, content: text || "Go on." };
      const assistant = {
        id: uid(),
        role: "assistant" as const,
        content: mockReply(text, selected.report),
      };
      patch(selected.id, {
        messages: [...selected.messages, user, assistant],
      });
      return;
    }

    const url = isYouTubeUrl(text) ? text.trim() : selected.youtubeUrl;
    if (!url && !selected.videoName) {
      if (text.trim()) {
        patch(selected.id, { youtubeUrl: text.trim() });
      }
      return;
    }
    startAnalysis(selected.id, {
      youtubeUrl: url || selected.youtubeUrl,
      report: STREET_FOOD_REPORT,
    });
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
      report: STREET_FOOD_REPORT,
      title: "Analyzing…",
    });
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
              onUrl={(youtubeUrl) => patch(selected.id, { youtubeUrl })}
              onVideo={(file) =>
                patch(selected.id, {
                  videoName: file.name,
                  videoPreview: URL.createObjectURL(file),
                })
              }
              onScreenshot={(file) =>
                patch(selected.id, {
                  screenshotName: file.name,
                  screenshotPreview: URL.createObjectURL(file),
                })
              }
              onSample={runSample}
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
            onAttachVideo={(file) =>
              patch(selected.id, {
                videoName: file.name,
                videoPreview: URL.createObjectURL(file),
              })
            }
            onAttachScreenshot={(file) =>
              patch(selected.id, {
                screenshotName: file.name,
                screenshotPreview: URL.createObjectURL(file),
              })
            }
            onRemoveVideo={() =>
              patch(selected.id, { videoName: null, videoPreview: null })
            }
            onRemoveScreenshot={() =>
              patch(selected.id, {
                screenshotName: null,
                screenshotPreview: null,
              })
            }
            onSuggestion={(text) => handleSend(text)}
          />
        )}
      </section>
    </div>
  );
}


