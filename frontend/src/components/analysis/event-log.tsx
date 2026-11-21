"use client";

import { ChevronDown, ChevronUp, Radio } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { formatTime } from "@/lib/format";
import type { ProgressEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const TYPE_LABEL: Record<string, string> = {
  run: "ANALİZ",
  step: "ADIM",
  pause: "DURAKLADI",
  pause_skipped: "ATLANDI",
  resume: "DEVAM",
};

/** Collapsible, timestamped live log at the bottom of the analysis screen. */
export function EventLog({
  events,
  connected,
}: {
  events: ProgressEvent[];
  connected: boolean;
}) {
  const [open, setOpen] = React.useState(true);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Scroll the log itself, not the page: scrollIntoView would drag the whole
  // analysis screen down on every event.
  React.useEffect(() => {
    const node = scrollRef.current;
    if (open && node) node.scrollTop = node.scrollHeight;
  }, [events.length, open]);

  return (
    <section className="rounded-lg border border-border bg-surface">
      <div className="flex items-center justify-between gap-3 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Radio
            className={cn(
              "h-3.5 w-3.5",
              connected ? "text-level-low" : "text-muted-foreground",
            )}
            aria-hidden
          />
          <h2 className="text-sm font-medium">Canlı olay günlüğü</h2>
          <Badge variant={connected ? "success" : "default"}>
            {connected ? "Bağlı (SSE)" : "Bağlantı bekleniyor"}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {events.length} olay
          </span>
        </div>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-surface-muted"
          aria-expanded={open}
        >
          {open ? (
            <>
              Daralt <ChevronDown className="h-3.5 w-3.5" aria-hidden />
            </>
          ) : (
            <>
              Genişlet <ChevronUp className="h-3.5 w-3.5" aria-hidden />
            </>
          )}
        </button>
      </div>

      {open ? (
        <div
          ref={scrollRef}
          className="max-h-56 overflow-y-auto border-t border-border px-4 py-2 font-mono text-[11px] leading-relaxed"
          role="log"
          aria-live="polite"
        >
          {events.length === 0 ? (
            <p className="py-3 text-muted-foreground">
              Henüz olay yok. Analiz başladığında adımlar burada akacak.
            </p>
          ) : (
            events.map((event, index) => (
              <div
                key={`${event.ts}-${index}`}
                className="flex gap-2 border-b border-border/50 py-1 last:border-0"
              >
                <span className="shrink-0 text-muted-foreground">
                  {formatTime(event.ts)}
                </span>
                <span className="w-20 shrink-0 text-accent">
                  {TYPE_LABEL[event.type] ?? event.type.toUpperCase()}
                </span>
                <span className="w-7 shrink-0 text-muted-foreground">
                  {event.step ? `#${event.step}` : ""}
                </span>
                <span className="min-w-0 flex-1 break-words">
                  {event.message ?? event.status ?? ""}
                  {event.placeholder ? (
                    <span className="ml-1 text-muted-foreground">
                      [örnek veri]
                    </span>
                  ) : null}
                </span>
              </div>
            ))
          )}
        </div>
      ) : null}
    </section>
  );
}
