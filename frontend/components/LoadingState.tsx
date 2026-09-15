import { LOADING_STEPS } from "@/lib/mock-data";
import { cn } from "@/lib/format";

export function LoadingState({ step }: { step: number }) {
  return (
    <article className="mx-auto w-full max-w-[720px] px-6 pt-10 pb-16">
      <h2 className="text-[28px] leading-[1.2] font-semibold tracking-tight text-[#111]">
        Analyzing your Short
      </h2>
      <p className="mt-3 text-[16px] leading-7 text-[#555]">
        Gemini is watching the whole video with audio and reading the retention
        chart. This usually takes 10–30 seconds.
      </p>
      <ol className="mt-8 space-y-3">
        {LOADING_STEPS.map((label, i) => {
          const done = i < step;
          const current = i === step;
          return (
            <li key={label} className="flex items-center gap-3 text-[15px]">
              <span
                className={cn(
                  "flex h-5 w-5 items-center justify-center rounded-full text-[11px]",
                  done && "bg-[#16a34a] text-white",
                  current && "border-2 border-accent",
                  !done && !current && "border border-[#e4e4e7]",
                )}
              >
                {done ? "✓" : ""}
                {current && (
                  <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
                )}
              </span>
              <span
                className={cn(
                  current && "font-medium text-[#111]",
                  done && "text-[#666]",
                  !done && !current && "text-[#b0b0b4]",
                )}
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </article>
  );
}
