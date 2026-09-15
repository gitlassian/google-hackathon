export type Rating = "strong" | "ok" | "weak";

export type CurvePoint = {
  t: number;
  pct: number;
};

export type Dip = {
  t: string;
  dropPct: number;
  onScreen: string;
  cause: string;
  fix: string;
};

export type Report = {
  score: number;
  verdict: string;
  extracted: {
    durationSec: number;
    stayedToWatchPct: number;
    avgViewDurationSec: number;
    curve: CurvePoint[];
  };
  hook: {
    rating: Rating;
    firstThreeSeconds: string;
    whyItWorksOrFails: string;
    rewrite: string;
  };
  dips: Dip[];
  stayedToWatch: {
    rating: Rating;
    explanation: string;
  };
  nextVideoRules: string[];
  distributionNote?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export type AnalysisStatus = "draft" | "loading" | "ready";

export type Analysis = {
  id: string;
  title: string;
  status: AnalysisStatus;
  youtubeUrl: string;
  videoName: string | null;
  screenshotName: string | null;
  screenshotPreview: string | null;
  videoPreview: string | null;
  report: Report | null;
  messages: ChatMessage[];
  loadingStep: number;
};

export type NavId = "analyses" | "settings";
