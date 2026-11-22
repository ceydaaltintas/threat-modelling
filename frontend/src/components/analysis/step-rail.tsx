"use client";

import { AlertCircle, Check, Loader2, Pause, UserCheck } from "lucide-react";
import * as React from "react";

import { Progress } from "@/components/ui/progress";
import type { RunStep, StepInfo, StepStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Short names for the rail. The full name belongs in the step header, not
 * nine times across the top of the screen.
 */
const SHORT_NAMES: Record<number, string> = {
  1: "Doküman",
  2: "Sistem modeli",
  3: "Bilgi",
  4: "Tehditler",
  5: "Doğrulama",
  6: "Risk",
  7: "Önlemler",
  8: "İnceleme",
  9: "Rapor",
};

const STATUS_TEXT: Record<StepStatus, string> = {
  pending: "Bekliyor",
  running: "Çalışıyor",
  done: "Tamam",
  failed: "Hata",
  waiting_user: "Sizi bekliyor",
  skipped: "Atlandı",
};

function Marker({ status, index }: { status: StepStatus; index: number }) {
  const base =
    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold transition-colors";
  switch (status) {
    case "done":
      return (
        <span className={cn(base, "border-level-low bg-level-low text-white")}>
          <Check className="h-3.5 w-3.5" aria-hidden />
        </span>
      );
    case "running":
      return (
        <span className={cn(base, "border-accent bg-accent text-white")}>
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
        </span>
      );
    case "failed":
      return (
        <span
          className={cn(base, "border-level-critical bg-level-critical text-white")}
        >
          <AlertCircle className="h-3.5 w-3.5" aria-hidden />
        </span>
      );
    case "waiting_user":
      return (
        <span className={cn(base, "border-level-high bg-level-high text-white")}>
          <UserCheck className="h-3.5 w-3.5" aria-hidden />
        </span>
      );
    default:
      return (
        <span className={cn(base, "border-border bg-surface text-muted-foreground")}>
          {index}
        </span>
      );
  }
}

/**
 * The nine steps as one horizontal rail across the top of the analysis
 * screen: where the run is, in one glance, without reading paragraphs.
 */
export function StepRail({
  definitions,
  steps,
  selected,
  onSelect,
  modelApprovalAfterStep,
  pauseStep,
}: {
  definitions: StepInfo[];
  steps: RunStep[];
  selected: number | null;
  onSelect: (stepNo: number) => void;
  modelApprovalAfterStep: number;
  pauseStep: number | null;
}) {
  const byNo = React.useMemo(
    () => new Map(steps.map((step) => [step.step_no, step])),
    [steps],
  );
  const active = steps.find((step) => step.status === "running");
  const done = steps.filter((step) => step.status === "done").length;

  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2.5">
      <ol className="flex items-start gap-0.5" aria-label="Analiz adımları">
        {definitions.map((definition) => {
          const step = byNo.get(definition.no);
          const status: StepStatus = step?.status ?? "pending";
          const isSelected = selected === definition.no;
          const paused = pauseStep === definition.no;
          const gate = definition.no === modelApprovalAfterStep;
          // A step that has not started has nothing to show, and opening it
          // would offer actions on data the pipeline has not produced yet.
          const reachable = status !== "pending";

          return (
            <React.Fragment key={definition.no}>
              <li className="min-w-0 flex-1">
                <button
                  type="button"
                  onClick={() => onSelect(definition.no)}
                  disabled={!reachable}
                  aria-current={isSelected ? "step" : undefined}
                  title={
                    (reachable
                      ? `${definition.no}. ${definition.name} — ${STATUS_TEXT[status]}`
                      : `${definition.no}. ${definition.name} — henüz çalışmadı`) +
                    (gate ? " · ardından model onayı için durur" : "")
                  }
                  className={cn(
                    "flex w-full flex-col items-center gap-1 rounded-md px-1 py-1 transition-colors",
                    isSelected ? "bg-accent-subtle" : "hover:bg-surface-muted",
                    !reachable && "cursor-not-allowed opacity-55 hover:bg-transparent",
                  )}
                >
                  <span className="relative">
                    <Marker status={status} index={definition.no} />
                    {gate ? (
                      // The approval stop belongs to the step it follows.
                      // On its own between two steps it had nothing to
                      // attach to and read as stray furniture.
                      <span
                        className={cn(
                          "absolute -bottom-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full border-2 border-surface",
                          paused
                            ? "bg-level-high text-white"
                            : "bg-muted-foreground/60 text-surface",
                        )}
                        aria-hidden
                      >
                        <Pause className="h-2 w-2" />
                      </span>
                    ) : null}
                  </span>
                  <span
                    className={cn(
                      "w-full truncate text-center text-[11px] leading-tight",
                      isSelected
                        ? "font-medium text-accent"
                        : status === "pending"
                          ? "text-muted-foreground"
                          : "text-foreground",
                    )}
                  >
                    {SHORT_NAMES[definition.no] ?? definition.name}
                  </span>
                </button>
              </li>

            </React.Fragment>
          );
        })}
      </ol>

      {/* One line of live detail, only for the step that is actually busy. */}
      {active ? (
        <div className="mt-2 flex items-center gap-2 border-t border-border pt-2">
          <Progress
            value={active.progress}
            className="h-1 max-w-[180px] flex-1"
            label={`${active.name} ilerlemesi`}
          />
          <span className="min-w-0 flex-1 truncate text-[11px] text-muted-foreground">
            {active.message}
          </span>
          <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
            {done}/{definitions.length}
          </span>
        </div>
      ) : null}
    </div>
  );
}
