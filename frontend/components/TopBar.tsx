import { FileText, Menu } from "lucide-react";

type Props = {
  title: string;
  onOpenSidebar?: () => void;
};

export function TopBar({ title, onOpenSidebar }: Props) {
  return (
    <header className="relative flex h-12 shrink-0 items-center justify-center gap-2 border-b border-line px-3">
      <button
        type="button"
        onClick={onOpenSidebar}
        className="absolute left-3 flex h-8 w-8 items-center justify-center rounded-lg text-[#555] hover:bg-[#f4f4f5] md:hidden"
        aria-label="Open sidebar"
      >
        <Menu className="h-[18px] w-[18px]" />
      </button>
      <FileText className="h-4 w-4 text-[#8e8e93]" />
      <h1 className="max-w-[min(760px,calc(100%-4rem))] truncate text-[14px] font-medium tracking-[-0.01em] text-[#111]">
        {title}
      </h1>
    </header>
  );
}
