import { FileText, Plus, Settings, SquarePen } from "lucide-react";
import { cn } from "@/lib/format";
import type { Analysis, NavId } from "@/lib/types";

type Props = {
  analyses: Analysis[];
  selectedId: string | null;
  nav: NavId;
  onSelect: (id: string) => void;
  onNew: () => void;
  onNav: (nav: NavId) => void;
};

export function Sidebar({
  analyses,
  selectedId,
  nav,
  onSelect,
  onNew,
  onNav,
}: Props) {
  return (
    <aside className="flex h-full w-[232px] shrink-0 flex-col bg-sidebar text-[13px]">
      <div className="flex items-center justify-end px-3 pt-3 pb-2">
        <button
          type="button"
          onClick={onNew}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[#555] hover:bg-[#ececee]"
          aria-label="New analysis"
        >
          <SquarePen className="h-[18px] w-[18px]" />
        </button>
      </div>

      <div className="px-3 pt-2 pb-1">
        <div className="px-2 pb-1 text-[12px] text-muted">Analyses</div>
        <button
          type="button"
          onClick={onNew}
          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[#222] hover:bg-[#ececee]"
        >
          <Plus className="h-3.5 w-3.5" />
          New analysis
        </button>
      </div>

      <nav className="thin-scroll mt-1 flex-1 overflow-y-auto px-3 pb-3">
        <ul className="flex flex-col gap-0.5">
          {analyses.map((item) => {
            const active = nav === "analyses" && item.id === selectedId;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => {
                    onNav("analyses");
                    onSelect(item.id);
                  }}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-[10px] px-2 py-[7px] text-left text-[13px] leading-tight",
                    active
                      ? "bg-white text-[#111] shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
                      : "text-[#444] hover:bg-[#ececee]",
                  )}
                >
                  <FileText className="h-3.5 w-3.5 shrink-0 text-[#8e8e93]" />
                  <span className="truncate">{item.title}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="px-3 pt-1 pb-4">
        <button
          type="button"
          onClick={() => onNav("settings")}
          className={cn(
            "flex w-full items-center gap-2 rounded-[10px] px-2 py-2 text-left text-[13px]",
            nav === "settings"
              ? "bg-white text-[#111] shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
              : "text-[#444] hover:bg-[#ececee]",
          )}
        >
          <Settings className="h-[16px] w-[16px]" />
          Settings
        </button>
      </div>
    </aside>
  );
}
