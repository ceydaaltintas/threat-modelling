"use client";

import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Loader2,
  PauseCircle,
  UserCheck,
} from "lucide-react";
import * as React from "react";

import { Progress } from "@/components/ui/progress";
import { elapsedBetween, formatDuration } from "@/lib/format";
import type { RunStep, StepInfo, StepStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_LABEL: Record<StepStatus, string> = {
  pending: "Bekliyor",
  running: "Çalışıyor",
  done: "Tamam",
  failed: "Hata",
  waiting_user: "Kullanıcı bekleniyor",
  skipped: "Atlandı",
};

function StatusIcon({ status }: { status: StepStatus }) {
  const common = "h-4 w-4 shrink-0";
  switch (status) {
    case "running":
      return (
        <Loader2 className={cn(common, "animate-spin text-accent")} aria-hidden />
      );
    case "done":
      return <CheckCircle2 className={cn(common, "text-level-low")} aria-hidden />;
    case "failed":
      return (
        <AlertCircle className={cn(common, "text-level-critical")} aria-hidden />
      );
    case "waiting_user":
      return <UserCheck className={cn(common, "text-level-high")} aria-hidden />;
    case "skipped":
      return <Circle className={cn(common, "text-muted-foreground")} aria-hidden />;
    default:
      return <Circle className={cn(common, "text-muted-foreground")} aria-hidden />;
  }
}

// The stepper stays scannable: only the headline counters appear here, in
// the order the step declared them. The detail panel shows all of them.
const STEPPER_COUNTER_LIMIT = 3;

/** "11 bileşen · 14 akış" from the counters the step reported. */
function countersText(
  counters: Record<string, number> | null,
  labels: Record<string, string>,
): string | null {
  if (!counters) return null;
  const order = Object.keys(labels);
  const parts = Object.entries(counters)
    .filter(([, value]) => typeof value === "number")
    .sort(([a], [b]) => order.indexOf(a) - order.indexOf(b))
    .slice(0, STEPPER_COUNTER_LIMIT)
    .map(([key, value]) => `${value} ${labels[key] ?? key}`);
  return parts.length > 0 ? parts.join(" · ") : null;
}

export interface StepperProps {
  definitions: StepInfo[];
  steps: RunStep[];
  selected: number | null;
  onSelect: (stepNo: number) => void;
  modelApprovalAfterStep: number;
  pauseStep: number | null;
}

export function Stepper({
  definitions,
  steps,
  selected,
  onSelect,
  modelApprovalAfterStep,
  pauseStep,
}: StepperProps) {
  const byNo = React.useMemo(
    () => new Map(steps.map((step) => [step.step_no, step])),
    [steps],
  );

  return (
    <ol className="space-y-1" aria-label="Analiz adımları">
      {definitions.map((definition, index) => {
        const step = byNo.get(definition.no);
        const status: StepStatus = step?.status ?? "pending";
        const reachable = status !== "pending";
        const isSelected = selected === definition.no;
        const duration = elapsedBetween(
          step?.started_at,
          step?.finished_at ?? (status === "running" ? null : step?.started_at),
        );
        const counters = countersText(
          step?.counters ?? null,
          definition.counter_labels,
        );
        const showApprovalGate =
          definition.no === modelApprovalAfterStep &&
          index < definitions.length - 1;

        return (
          <li key={definition.no}>
            <button
              type="button"
              onClick={() => onSelect(definition.no)}
              aria-current={isSelected ? "step" : undefined}
              className={cn(
                "w-full rounded-md border px-3 py-2.5 text-left transition-colors",
                isSelected
                  ? "border-accent/40 bg-accent-subtle"
                  : "border-transparent hover:bg-surface-muted",
                !reachable && "opacity-70",
              )}
            >
              <div className="flex items-start gap-2.5">
                <span className="mt-0.5">
                  <StatusIcon status={status} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate text-sm font-medium">
                      <span className="text-muted-foreground">{definition.no}.</span>{" "}
                      {definition.name}
                    </span>
                    {status === "running" || status === "done" ? (
                      <span className="shrink-0 text-[11px] text-muted-foreground">
                        {formatDuration(duration)}
                      </span>
                    ) : null}
                  </div>

                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    {STATUS_LABEL[status]}
                    {counters ? ` · ${counters}` : ""}
                  </p>

                  {status === "running" ? (
                    <div className="mt-2 space-y-1">
                      <Progress
                        value={step?.progress ?? 0}
                        label={`${definition.name} ilerlemesi`}
                      />
                      {step?.message ? (
                        <p className="truncate text-[11px] text-accent">
                          {step.message}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </div>
            </button>

            {showApprovalGate ? (
              <div
                className={cn(
                  "my-1 ml-6 flex items-center gap-2 rounded-md border border-dashed px-2.5 py-1.5 text-[11px]",
                  pauseStep === modelApprovalAfterStep
                    ? "border-level-high/50 bg-level-high/10 text-level-high"
                    : "border-border text-muted-foreground",
                )}
              >
                <PauseCircle className="h-3.5 w-3.5 shrink-0" aria-hidden />
                <span>Model onayı · duraklama noktası</span>
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
