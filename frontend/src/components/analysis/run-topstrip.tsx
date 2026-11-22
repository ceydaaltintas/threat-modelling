"use client";

import { Cpu, RotateCcw, Square, Timer } from "lucide-react";
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
  onCancel,
  busy,
  readOnly,
}: {
  run: Run | null;
  projectName: string;
  status: RunStatus | "connecting";
  llm: LlmUsage;
  onRestart: () => void;
  onCancel: () => void;
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
  // Stopping only makes sense while something is still going to happen.
  const active =
    status === "running" || status === "waiting_user" || status === "pending";

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface px-4 py-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-base font-semibold">{projectName}</h1>
          <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>
        </div>
        <p
          className="mt-0.5 truncate font-mono text-[10px] text-muted-foreground/70"
          title={run?.id ?? ""}
        >
          {run?.id ? `${run.id.slice(0, 8)}…` : "—"}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span
          className="flex items-center gap-1.5"
          title="Analizin başlangıcından bu yana geçen süre"
        >
          <Timer className="h-3.5 w-3.5" aria-hidden />
          <strong className="text-foreground">{formatDuration(elapsed)}</strong>
        </span>
        <span
          className="flex items-center gap-1.5"
          title={`${formatNumber(llm.calls)} LLM çağrısı, ${formatNumber(llm.tokens)} token`}
        >
          <Cpu className="h-3.5 w-3.5" aria-hidden />
          <strong className="text-foreground">{formatNumber(llm.calls)}</strong>
          <span>çağrı</span>
        </span>
        {llm.cached > 0 ? (
          <Badge variant="accent" title="Yanıt kayıttan geldi, yeni çağrı yapılmadı">
            {llm.cached} önbellekten
          </Badge>
        ) : null}
        {active ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={onCancel}
            disabled={busy || readOnly}
            title="Analizi durdur; kaldığı yerden yeniden çalıştırabilirsiniz"
          >
            <Square aria-hidden /> Durdur
          </Button>
        ) : null}
        <Button
          variant="ghost"
          size="sm"
          onClick={onRestart}
          disabled={busy || readOnly}
          title="Tüm analizi 1. adımdan baştan çalıştırır; mevcut sonuçlar ve kararlar silinir"
        >
          <RotateCcw aria-hidden /> Baştan çalıştır
        </Button>
      </div>
    </div>
  );
}
