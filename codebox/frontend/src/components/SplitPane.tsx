import { useCallback, useRef, useState, type ReactNode } from "react";
import { storageGet, storageSet } from "../lib/format";

/** Two resizable panes. On narrow screens the parent can stack them instead. */
export function SplitPane({
  direction,
  first,
  second,
  initial = 50,
  min = 20,
  storageKey,
  className = "",
}: {
  direction: "horizontal" | "vertical";
  first: ReactNode;
  second: ReactNode;
  initial?: number;
  min?: number;
  storageKey?: string;
  className?: string;
}) {
  const [size, setSize] = useState(() => {
    const saved = storageKey ? Number(storageGet(storageKey)) : NaN;
    return Number.isFinite(saved) && saved >= min && saved <= 100 - min ? saved : initial;
  });
  const container = useRef<HTMLDivElement>(null);
  const horizontal = direction === "horizontal";

  const startDrag = useCallback(
    (event: React.PointerEvent) => {
      event.preventDefault();
      const rect = container.current!.getBoundingClientRect();
      const move = (e: PointerEvent) => {
        const pct = horizontal
          ? ((e.clientX - rect.left) / rect.width) * 100
          : ((e.clientY - rect.top) / rect.height) * 100;
        const clamped = Math.min(100 - min, Math.max(min, pct));
        setSize(clamped);
        if (storageKey) storageSet(storageKey, String(clamped));
      };
      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };
      document.body.style.cursor = horizontal ? "col-resize" : "row-resize";
      document.body.style.userSelect = "none";
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
    },
    [horizontal, min, storageKey],
  );

  return (
    <div ref={container} className={`flex min-h-0 min-w-0 ${horizontal ? "flex-row" : "flex-col"} ${className}`}>
      <div className="flex min-h-0 min-w-0 flex-col overflow-hidden" style={{ flexBasis: `${size}%` }}>
        {first}
      </div>
      <div
        role="separator"
        aria-orientation={horizontal ? "vertical" : "horizontal"}
        onPointerDown={startDrag}
        className={`group relative shrink-0 bg-line transition-colors hover:bg-accent/60 ${
          horizontal ? "w-px cursor-col-resize" : "h-px cursor-row-resize"
        }`}
      >
        <span className={`absolute ${horizontal ? "inset-y-0 -left-1.5 -right-1.5" : "inset-x-0 -top-1.5 -bottom-1.5"}`} />
      </div>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">{second}</div>
    </div>
  );
}
