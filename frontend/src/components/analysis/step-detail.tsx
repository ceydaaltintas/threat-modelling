"use client";

import { ChevronDown, Info, ListChecks, RefreshCw } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { elapsedBetween, formatDateTime, formatDuration } from "@/lib/format";
import type { RunStep, StepInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * The header above a step's output.
 *
 * Deliberately one line plus chips: the long explanation of what the step
 * does is behind a disclosure, because it is read once and then never
 * again, while the output below is read every time.
 */
export function StepDetail({
  definition,
  step,
  paused,
  pauseReason,
  onResume,
  onRetry,
  busy,
  readOnly,
  content,
}: {
  definition: StepInfo | null;
  step: RunStep | null;
  paused: boolean;
  pauseReason: string | null;
  onResume: () => void;
  onRetry: () => void;
  busy: boolean;
  readOnly: boolean;
  content?: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(false);

  if (!definition) {
    return (
      <EmptyState
        icon={ListChecks}
        title="Adım seçilmedi"
        description="Yukarıdan bir adıma tıklayın."
      />
    );
  }

  const counters = Object.entries(step?.counters ?? {}).filter(
    ([, value]) => typeof value === "number",
  );
  // Most of these say the same thing twice: on step 8, "78 tehdit" plus
  // "1 karar verildi" plus "77 bekleyen" plus the breakdown of that 1 is
  // one fact written four ways. The first counter is the step's own total;
  // after it, only what is not zero is worth a word, and the rest moves
  // into "Ne yapar?" rather than disappearing.
  const headline = counters.slice(0, 1);
  const rest = counters.slice(1);
  const notable = rest.filter(([, value]) => value !== 0).slice(0, 2);
  const folded = rest.filter(([key]) => !notable.some(([k]) => k === key));
  const shown = [...headline, ...notable];
  const duration = elapsedBetween(step?.started_at, step?.finished_at);
  const failed = step?.status === "failed";

  const resumeLabel =
    pauseReason === "expert_review"
      ? "İncelemeyi tamamla ve devam et"
      : "Onayla ve devam et";

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 className="text-base font-semibold">
            <span className="text-muted-foreground">{definition.no}.</span>{" "}
            {definition.name}
          </h2>
          {duration !== null && step?.status === "done" ? (
            <span className="text-[11px] text-muted-foreground">
              {formatDuration(duration)}
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="flex items-center gap-0.5 text-[11px] text-muted-foreground hover:text-accent"
          >
            Ne yapar?
            <ChevronDown
              className={cn("h-3 w-3 transition-transform", open && "rotate-180")}
              aria-hidden
            />
          </button>
        </div>

        {shown.length > 0 ? (
          <p className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
            {shown.map(([key, value]) => (
              <span key={key}>
                <strong className="font-semibold tabular-nums text-foreground">
                  {value}
                </strong>{" "}
                {definition.counter_labels[key] ?? key}
              </span>
            ))}
            {folded.length > 0 ? (
              <button
                type="button"
                onClick={() => setOpen(true)}
                className="text-[11px] text-muted-foreground underline-offset-2 hover:text-accent hover:underline"
              >
                +{folded.length} sayı
              </button>
            ) : null}
          </p>
        ) : null}

        {open ? (
          <div className="rounded-md border border-border bg-surface-muted p-3 text-xs text-muted-foreground">
            <p>{definition.description}</p>
            <p className="mt-1.5">
              Başlangıç: {formatDateTime(step?.started_at)} · Bitiş:{" "}
              {formatDateTime(step?.finished_at)} · Yapan:{" "}
              {
                {
                  code: "Sistem (kod)",
                  llm: "Yapay zekâ",
                  "code+llm": "Kod ve yapay zekâ",
                  human: "Güvenlik uzmanı",
                }[definition.performer]
              }
            </p>
            {folded.length > 0 ? (
              <p className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
                {folded.map(([key, value]) => (
                  <span key={key}>
                    <strong className="font-semibold tabular-nums">
                      {value}
                    </strong>{" "}
                    {definition.counter_labels[key] ?? key}
                  </span>
                ))}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>

      {failed ? (
        <div className="space-y-2 rounded-md border border-level-critical/40 bg-level-critical/10 p-3">
          <p className="text-sm font-medium text-level-critical">
            Bu adım hata ile durdu
          </p>
          <p className="text-xs text-muted-foreground">
            {step?.message ?? "Ayrıntı için olay günlüğüne bakın."}
          </p>
          <Button variant="outline" size="sm" onClick={onRetry} disabled={readOnly}>
            <RefreshCw aria-hidden /> Bu adımı yeniden dene
          </Button>
        </div>
      ) : null}

      {paused ? (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-level-high/40 bg-level-high/10 p-3">
          <p className="min-w-0 flex-1 text-sm">
            {pauseReason === "expert_review"
              ? "Tehditleri inceleyin, sonra devam edin."
              : "Sistem modelini inceleyin, gerekiyorsa düzenleyin."}
          </p>
          <Button onClick={onResume} disabled={busy || readOnly}>
            {resumeLabel}
          </Button>
          {readOnly ? (
            <p className="w-full text-[11px] text-muted-foreground">
              Yönetici rolü salt okunurdur; devam etmek için Güvenlik Uzmanı
              rolüne geçin.
            </p>
          ) : null}
        </div>
      ) : null}

      {content ?? (
        <p className="flex items-center gap-2 rounded-md border border-dashed border-border p-4 text-xs text-muted-foreground">
          <Info className="h-3.5 w-3.5 shrink-0" aria-hidden />
          Bu adım tamamlandığında çıktısı burada görünecek.
        </p>
      )}
    </div>
  );
}
