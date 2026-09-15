"use client";

import { useState } from "react";

const KEY = "coach.geminiApiKey";

export function SettingsPanel() {
  const [apiKey, setApiKey] = useState(() =>
    typeof window === "undefined" ? "" : (localStorage.getItem(KEY) ?? ""),
  );
  const [saved, setSaved] = useState(false);

  return (
    <article className="mx-auto w-full max-w-[640px] px-6 pt-10 pb-16">
      <h2 className="text-[28px] leading-[1.2] font-semibold tracking-tight text-[#111]">
        Settings
      </h2>
      <p className="mt-3 text-[16px] leading-7 text-[#555]">
        Nothing leaves this browser tab. There is no account and no database —
        the analysis lives in memory until you close the tab.
      </p>

      <h3 className="mt-8 text-[15px] font-semibold text-[#111]">Appearance</h3>
      <p className="mt-2 text-[15px] leading-7 text-[#444]">
        White theme only. Matches the Coach / Bionic / Ollama shell.
      </p>

      <h3 className="mt-8 text-[15px] font-semibold text-[#111]">Model</h3>
      <p className="mt-2 text-[15px] leading-7 text-[#444]">
        <strong>Gemini 3.8 Flash</strong> — static 1 fps, audio on. Fallback:
        Gemini 3.1 Pro. Used for the single analysis prompt and follow-up chat.
      </p>

      <h3 className="mt-8 text-[15px] font-semibold text-[#111]">
        Gemini API key
      </h3>
      <p className="mt-2 text-[15px] leading-7 text-[#444]">
        Stored in localStorage on this machine. Not wired to the backend yet —
        the UI currently plays a mock report.
      </p>
      <input
        type="password"
        value={apiKey}
        onChange={(e) => {
          setApiKey(e.target.value);
          setSaved(false);
        }}
        placeholder="AIza…"
        className="mt-3 w-full rounded-xl border border-line bg-white px-3 py-2.5 text-[14px]"
      />
      <button
        type="button"
        className="mt-3 h-8 rounded-lg bg-accent px-3 text-[13px] font-medium text-white hover:bg-[#1b6ff2]"
        onClick={() => {
          localStorage.setItem(KEY, apiKey.trim());
          setSaved(true);
        }}
      >
        {saved ? "Saved" : "Save key"}
      </button>
    </article>
  );
}
