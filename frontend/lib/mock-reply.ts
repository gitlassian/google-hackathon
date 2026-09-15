import { parseTimestamp } from "./format";
import type { Report } from "./types";

export function mockReply(message: string, report: Report): string {
  const lower = message.toLowerCase();
  const stamp = message.match(/\d+:\d{2}/)?.[0];

  if (stamp) {
    const dip = report.dips.find((d) => d.t === stamp);
    if (dip) {
      return `At ${dip.t} the curve drops ${dip.dropPct} points. On screen: ${dip.onScreen}. ${dip.cause} The fix for the next Short is not a recut of this one — ${dip.fix.charAt(0).toLowerCase()}${dip.fix.slice(1)}`;
    }
    const sec = parseTimestamp(stamp);
    const nearest = report.extracted.curve.reduce((best, p) =>
      Math.abs(p.t - sec) < Math.abs(best.t - sec) ? p : best,
    );
    return `Around ${stamp} the extracted curve sits near ${Math.round(nearest.pct)}%. The first-three-seconds window is still the main leak — ${report.hook.whyItWorksOrFails}`;
  }

  if (lower.includes("hook line") || lower.includes("3 hook")) {
    return `Three spoken hooks for this topic:\n\n1. “I sold 200 of these in 4 hours — watch the 12-second setup.”\n2. “If your first frame is a kitchen, they already swiped. Start on the food.”\n3. “This sandwich looks slow. It isn’t. Here’s the only cut that matters.”\n\nEach one states the payoff before 0:02 and can be burned as on-screen text.`;
  }

  if (lower.includes("first frame") || lower.includes("opening")) {
    return `The first frame should be the finished thing, filling the phone, with motion. Right now ${report.hook.firstThreeSeconds} That is why the 0–3s rating is ${report.hook.rating}. Next Short: ${report.hook.rewrite}`;
  }

  if (lower.includes("hook")) {
    return `Hook rating: ${report.hook.rating}. ${report.hook.whyItWorksOrFails}\n\nSuggested rewrite:\n${report.hook.rewrite}`;
  }

  if (lower.includes("rule") || lower.includes("next")) {
    const rules = report.nextVideoRules.map((r, i) => `${i + 1}. ${r}`).join("\n");
    return `Carry these into the next Short — do not recut this one:\n\n${rules}`;
  }

  return `${report.verdict} If you want the exact leak, look at ${report.dips[0]?.t ?? "0:03"}: ${report.dips[0]?.cause ?? report.hook.whyItWorksOrFails}`;
}
