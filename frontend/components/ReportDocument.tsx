"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { formatTime, parseTimestamp, ratingLabel } from "@/lib/format";
import type { Analysis, Rating } from "@/lib/types";
import { RetentionChart } from "./RetentionChart";
import { ScoreRing } from "./ScoreRing";
import { VideoPanel } from "./VideoPanel";

export function ReportDocument({ analysis }: { analysis: Analysis }) {
  const report = analysis.report;
  const [time, setTime] = useState(0);

  if (!report) return null;

  return (
    <article className="mx-auto w-full max-w-[760px] px-6 pt-9 pb-16">
      <div className="flex items-center gap-5">
        <ScoreRing score={report.score} />
        <div className="min-w-0">
          <div className="text-[13px] text-muted">
            {ratingLabel(report.hook.rating)} hook · {report.extracted.stayedToWatchPct}% stayed to watch
          </div>
          <h2 className="mt-1 text-[28px] leading-[1.2] font-semibold tracking-tight text-[#111]">
            {analysis.title}
          </h2>
        </div>
      </div>

      <p className="mt-5 text-[16.5px] leading-[1.7] text-[#222]">
        {report.verdict}
      </p>

      <h3 className="mt-10 text-[20px] font-semibold tracking-tight text-[#111]">
        What the chart says
      </h3>
      <table className="mt-3 w-full text-[15px]">
        <thead>
          <tr className="text-left text-[#333]">
            <th className="border-b border-line py-2.5 font-medium">Metric</th>
            <th className="border-b border-line py-2.5 font-medium">Value</th>
          </tr>
        </thead>
        <tbody className="text-[#222]">
          <Row
            k="Duration"
            v={formatTime(report.extracted.durationSec)}
          />
          <Row
            k="Stayed to watch"
            v={`${report.extracted.stayedToWatchPct}% · ${ratingLabel(report.stayedToWatch.rating)}`}
          />
          <Row
            k="Average view duration"
            v={`${report.extracted.avgViewDurationSec}s`}
          />
        </tbody>
      </table>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.05fr_1fr]">
        <VideoPanel
          src={analysis.videoPreview}
          currentTime={time}
          durationSec={report.extracted.durationSec}
          onTime={setTime}
        />
        <div className="rounded-2xl border border-line bg-[#fcfcfc] p-2">
          <RetentionChart
            curve={report.extracted.curve}
            durationSec={report.extracted.durationSec}
            dips={report.dips}
            currentTime={time}
            onSeek={setTime}
          />
        </div>
      </div>
      <p className="mt-2 text-[12px] text-muted">
        Click a red marker or anywhere on the curve to seek {formatTime(time)}.
        Shorts curves can start above 100% because of rewatches.
      </p>

      <h3 className="mt-10 text-[20px] font-semibold tracking-tight text-[#111]">
        Hook (0–3 s)
      </h3>
      <p className="mt-3 text-[16px] leading-7 text-[#222]">
        <strong>Rating.</strong>{" "}
        <RatingChip rating={report.hook.rating} /> {ratingLabel(report.hook.rating)}.
      </p>
      <p className="mt-3 text-[16px] leading-7 text-[#222]">
        <strong>On screen.</strong> {report.hook.firstThreeSeconds}
      </p>
      <p className="mt-3 text-[16px] leading-7 text-[#222]">
        <strong>Why it {report.hook.rating === "strong" ? "works" : "fails"}.</strong>{" "}
        {report.hook.whyItWorksOrFails}
      </p>

      <CodeBlock label="rewrite" text={report.hook.rewrite} />

      <h3 className="mt-10 text-[20px] font-semibold tracking-tight text-[#111]">
        Dips
      </h3>
      <p className="mt-2 text-[15px] leading-7 text-[#555]">
        Each drop of more than 15 points in 3 seconds is a cliff. Click a row to
        seek the player.
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[560px] text-[14.5px]">
          <thead>
            <tr className="text-left text-[#333]">
              <th className="border-b border-line py-2.5 font-medium">Time</th>
              <th className="border-b border-line py-2.5 font-medium">Drop</th>
              <th className="border-b border-line py-2.5 font-medium">On screen</th>
              <th className="border-b border-line py-2.5 font-medium">Cause</th>
            </tr>
          </thead>
          <tbody>
            {report.dips.map((dip) => (
              <tr
                key={dip.t}
                className="cursor-pointer text-[#222] hover:bg-[#fafafa]"
                onClick={() => setTime(parseTimestamp(dip.t))}
              >
                <td className="border-b border-line py-3 font-medium text-accent">
                  {dip.t}
                </td>
                <td className="border-b border-line py-3">−{dip.dropPct} pts</td>
                <td className="border-b border-line py-3">{dip.onScreen}</td>
                <td className="border-b border-line py-3">{dip.cause}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="mt-4 list-disc space-y-2 pl-5 text-[16px] leading-7 text-[#222]">
        {report.dips.map((dip) => (
          <li key={`${dip.t}-fix`}>
            <strong>Fix at {dip.t}.</strong> {dip.fix}
          </li>
        ))}
      </ul>

      <h3 className="mt-10 text-[20px] font-semibold tracking-tight text-[#111]">
        Stayed to watch
      </h3>
      <p className="mt-3 text-[16px] leading-7 text-[#222]">
        <RatingChip rating={report.stayedToWatch.rating} />{" "}
        <strong>{ratingLabel(report.stayedToWatch.rating)}.</strong>{" "}
        {report.stayedToWatch.explanation}
      </p>

      <h3 className="mt-10 text-[20px] font-semibold tracking-tight text-[#111]">
        Rules for your next Short
      </h3>
      <p className="mt-2 text-[15px] leading-7 text-[#555]">
        Actionable on the next video — not a recut of this one.
      </p>
      <ol className="mt-3 list-decimal space-y-2 pl-5 text-[16px] leading-7 text-[#222]">
        {report.nextVideoRules.map((rule) => (
          <li key={rule}>{rule}</li>
        ))}
      </ol>

      {report.distributionNote && (
        <>
          <h3 className="mt-10 text-[20px] font-semibold tracking-tight text-[#111]">
            Distribution
          </h3>
          <p className="mt-3 text-[16px] leading-7 text-[#222]">
            {report.distributionNote}
          </p>
        </>
      )}

      {analysis.messages.length > 0 && (
        <div className="mt-12 border-t border-line pt-8">
          {analysis.messages.map((m) =>
            m.role === "user" ? (
              <p
                key={m.id}
                className="mt-6 text-[16px] font-semibold tracking-tight text-[#111]"
              >
                {m.content}
              </p>
            ) : (
              <p
                key={m.id}
                className="mt-3 whitespace-pre-wrap text-[16px] leading-7 text-[#222]"
              >
                {m.content}
              </p>
            ),
          )}
        </div>
      )}
    </article>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <tr>
      <td className="border-b border-line py-3 text-[#333]">{k}</td>
      <td className="border-b border-line py-3">{v}</td>
    </tr>
  );
}

function RatingChip({ rating }: { rating: Rating }) {
  const cls =
    rating === "strong"
      ? "bg-emerald-50 text-emerald-700"
      : rating === "ok"
        ? "bg-amber-50 text-amber-800"
        : "bg-red-50 text-red-700";
  return (
    <span
      className={`mr-1 inline-flex rounded-full px-2 py-0.5 text-[12px] font-medium ${cls}`}
    >
      {ratingLabel(rating)}
    </span>
  );
}

function CodeBlock({ label, text }: { label: string; text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative mt-5 overflow-hidden rounded-xl bg-[#f4f4f5]">
      <div className="flex items-center justify-between px-4 pt-3 text-[12px] text-muted">
        <span>{label}</span>
        <button
          type="button"
          className="inline-flex items-center gap-1 text-[12px] hover:text-[#111]"
          onClick={async () => {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 1200);
          }}
        >
          {copied ? (
            <Check className="h-3.5 w-3.5" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
          Copy
        </button>
      </div>
      <pre className="px-4 pt-2 pb-4 text-[14px] leading-6 whitespace-pre-wrap text-[#1d4ed8]">
        {text}
      </pre>
    </div>
  );
}
