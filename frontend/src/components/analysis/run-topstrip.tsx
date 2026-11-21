"use client";

import { Cpu, Database, RotateCcw, Timer } from "lucide-react";
import * as React from "react";

import type { LlmUsage } from "@/components/analysis/use-run-stream";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { elapsedBetween, formatDuration, formatNumber } from "@/lib/format";
import type { Run, RunStatus } from "@/lib/types";

const STATUS_LABEL: Record<RunStatus | "connecting", string> = {
  connecting: "Bağlanıyor",
  pending: "Başlatılıyor",
  running: "Çalışıyor",
  waiting_user: "Kullanıcı bekleniyor",
  done: "Tamamlandı",
  failed: "Hata",
  cancelled: "İptal edildi",
};

const STATUS_VARIANT: Record<
  RunStatus | "connecting",
  "default" | "accent" | "success" | "warning" | "danger"
> = {
  connecting: "default",
  pending: "default",
  running: "accent",
  waiting_user: "warning",
  done: "success",
  failed: "danger",
  cancelled: "default",
};

export function RunTopStrip({
  run,
  projectName,
  status,
  llm,
  onRestart,
  busy,
  readOnly,
}: {
  run: Run | null;
  projectName: string;
  status: RunStatus | "connecting";
  llm: LlmUsage;
  onRestart: () => void;
  busy: boolean;
  readOnly: boolean;
}) {
  // Re-render once a second so the elapsed time ticks while a run is active.
  const [, force] = React.useState(0);
  React.useEffect(() => {
    if (status !== "running" && status !== "waiting_user") return;
    const id = window.setInterval(() => force((v) => v + 1), 1000);
    return () => window.clearInterval(id);
  }, [status]);

  const elapsed = elapsedBetween(run?.started_at, run?.finished_at);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface px-4 py-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-base font-semibold">{projectName}</h1>
          <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>
        </div>
        <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
          {run?.id ?? "—"}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <Timer className="h-3.5 w-3.5" aria-hidden />
          Geçen süre: <strong className="text-foreground">{formatDuration(elapsed)}</strong>
        </span>
        <span className="flex items-center gap-1.5">
          <Cpu className="h-3.5 w-3.5" aria-hidden />
          LLM çağrısı: <strong className="text-foreground">{formatNumber(llm.calls)}</strong>
        </span>
        <span className="flex items-center gap-1.5">
          <Database className="h-3.5 w-3.5" aria-hidden />
          Token: <strong className="text-foreground">{formatNumber(llm.tokens)}</strong>
        </span>
        {llm.cached > 0 || llm.replay ? (
          <Badge variant="accent">Önbellekten ({llm.cached})</Badge>
        ) : null}
        <Button
          variant="outline"
          size="sm"
          onClick={onRestart}
          disabled={busy || readOnly}
        >
          <RotateCcw aria-hidden /> Yeniden çalıştır
        </Button>
      </div>
    </div>
  );
}
