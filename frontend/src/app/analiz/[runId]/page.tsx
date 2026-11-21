"use client";

import { AlertCircle } from "lucide-react";
import { useParams } from "next/navigation";
import * as React from "react";

import { DocumentPanel } from "@/components/analysis/document-panel";
import { EventLog } from "@/components/analysis/event-log";
import { ReportPanel } from "@/components/analysis/report-panel";
import { RetrievalPanel } from "@/components/analysis/retrieval-panel";
import {
  MitigationSummary,
  RiskSummary,
  ValidationSummary,
} from "@/components/analysis/step-summaries";
import { ThreatTable } from "@/components/analysis/threat-table";
import { RunTopStrip } from "@/components/analysis/run-topstrip";
import { StepDetail } from "@/components/analysis/step-detail";
import { Stepper } from "@/components/analysis/stepper";
import { SystemModelPanel } from "@/components/analysis/system-model-panel";
import { useRunStream } from "@/components/analysis/use-run-stream";
import { useMeta } from "@/components/providers/meta-provider";
import { useRole } from "@/components/providers/role-provider";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import type { SystemModelData, SystemModelVersion } from "@/lib/system-model";
import type {
  DocumentOut,
  MitigationOutput,
  RetrievalOutput,
  RiskOutput,
  ReportOutput,
  ReviewAction,
  ThreatGenOutput,
  ThreatListResponse,
  ValidationOutput,
} from "@/lib/types";

export default function AnalysisPage() {
  const params = useParams<{ runId: string }>();
  const runId = params?.runId ?? null;
  const { meta, loading: metaLoading } = useMeta();
  const { readOnly } = useRole();
  const { toast } = useToast();

  const stream = useRunStream(runId);
  const [selected, setSelected] = React.useState<number | null>(null);
  const [pinned, setPinned] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  const [documents, setDocuments] = React.useState<DocumentOut[]>([]);
  const [model, setModel] = React.useState<SystemModelVersion | null>(null);
  const [savingModel, setSavingModel] = React.useState(false);
  const modelDirty = React.useRef(false);
  const [threats, setThreats] = React.useState<ThreatListResponse | null>(null);

  const stepStatus = (no: number) =>
    stream.steps.find((item) => item.step_no === no)?.status;

  // Load each step's output once that step reports done.
  const step1Done = stepStatus(1) === "done";
  const step2Done = stepStatus(2) === "done";
  const step4Done = stepStatus(4) === "done";
  // Steps 5-7 rewrite the threat rows, so reload when each finishes.
  const laterSteps = [5, 6, 7, 8].map(stepStatus).join(",");

  React.useEffect(() => {
    if (!runId || !step1Done) return;
    api.runDocuments(runId).then(setDocuments).catch(() => setDocuments([]));
  }, [runId, step1Done]);

  React.useEffect(() => {
    if (!runId || !step2Done) return;
    api
      .systemModel(runId)
      .then((value) => {
        // Never throw away an edit in progress.
        if (!modelDirty.current) setModel(value);
      })
      .catch(() => setModel(null));
  }, [runId, step2Done]);

  React.useEffect(() => {
    if (!runId || !step4Done) return;
    api.threats(runId).then(setThreats).catch(() => setThreats(null));
  }, [runId, step4Done, laterSteps]);

  // Follow the active step until the user picks one.
  React.useEffect(() => {
    if (pinned) return;
    const active =
      stream.steps.find((step) => step.status === "running") ??
      stream.steps.find((step) => step.status === "waiting_user") ??
      stream.steps.find((step) => step.status === "failed") ??
      [...stream.steps].reverse().find((step) => step.status === "done");
    if (active) setSelected(active.step_no);
  }, [stream.steps, pinned]);

  const definitions = meta?.steps ?? [];
  const definition = definitions.find((item) => item.no === selected) ?? null;
  const step = stream.steps.find((item) => item.step_no === selected) ?? null;
  const pausedHere = stream.pause !== null && stream.pause.step === selected;

  const resume = async () => {
    if (!runId) return;
    setBusy(true);
    try {
      await api.resumeRun(runId);
      toast({ title: "Analize devam ediliyor", tone: "success" });
    } catch (err) {
      toast({
        title: "Devam edilemedi",
        description: (err as Error).message,
        tone: "error",
      });
    } finally {
      setBusy(false);
    }
  };

  const retry = async (stepNo: number) => {
    if (!runId) return;
    setBusy(true);
    try {
      await api.retryStep(runId, stepNo);
      stream.reload();
      toast({
        title: `${stepNo}. adım yeniden çalıştırılıyor`,
        tone: "success",
      });
    } catch (err) {
      toast({
        title: "Adım yeniden çalıştırılamadı",
        description: (err as Error).message,
        tone: "error",
      });
    } finally {
      setBusy(false);
    }
  };

  const reloadThreats = React.useCallback(async () => {
    if (!runId) return;
    try {
      setThreats(await api.threats(runId));
    } catch {
      /* the table keeps the rows it has */
    }
  }, [runId]);

  const decide = React.useCallback(
    async (
      threatId: string,
      action: ReviewAction,
      extra?: {
        note?: string;
        likelihood?: number;
        impact?: number;
        reason?: string;
      },
    ) => {
      if (!runId) return;
      setBusy(true);
      try {
        await api.reviewThreat(runId, threatId, { action, ...extra });
        await reloadThreats();
      } catch (err) {
        toast({
          title: "Karar kaydedilemedi",
          description: (err as Error).message,
          tone: "error",
        });
      } finally {
        setBusy(false);
      }
    },
    [runId, reloadThreats, toast],
  );

  const decideBulk = React.useCallback(
    async (
      threatIds: string[],
      action: "accept" | "reject" | "false_positive" | "reset",
    ) => {
      if (!runId) return;
      setBusy(true);
      try {
        const result = await api.reviewBulk(runId, {
          threat_ids: threatIds,
          action,
        });
        await reloadThreats();
        toast({
          title: `${result.updated} tehdit güncellendi`,
          description: "Her işlem denetim izine yazıldı.",
          tone: "success",
        });
      } catch (err) {
        toast({
          title: "Toplu işlem başarısız",
          description: (err as Error).message,
          tone: "error",
        });
      } finally {
        setBusy(false);
      }
    },
    [runId, reloadThreats, toast],
  );

  const saveModel = async (data: SystemModelData, reason: string) => {
    if (!runId) return;
    setSavingModel(true);
    try {
      const saved = await api.saveSystemModel(runId, data, reason);
      modelDirty.current = false;
      setModel(saved);
      toast({
        title: `Sistem modeli kaydedildi (sürüm ${saved.version})`,
        description: "Değişiklik denetim izine yazıldı.",
        tone: "success",
      });
    } catch (err) {
      toast({
        title: "Model kaydedilemedi",
        description: (err as Error).message,
        tone: "error",
      });
      throw err;
    } finally {
      setSavingModel(false);
    }
  };

  const componentNames = React.useMemo(() => {
    const names: Record<string, string> = {};
    for (const component of model?.data.components ?? []) {
      names[component.id] = component.name;
    }
    return names;
  }, [model]);

  const stepOutput = (stepNo: number) =>
    stream.steps.find((item) => item.step_no === stepNo)?.output ?? null;

  const panelFor = (stepNo: number | null): React.ReactNode | undefined => {
    if (stepNo === 1 && documents.length > 0) {
      return <DocumentPanel documents={documents} />;
    }
    if (stepNo === 2 && model) {
      return (
        <SystemModelPanel
          version={model}
          documents={documents}
          onSave={saveModel}
          saving={savingModel}
          readOnly={readOnly}
          dirtyRef={modelDirty}
        />
      );
    }
    if (stepNo === 3) {
      const output = stepOutput(3) as RetrievalOutput | null;
      if (output?.elements) return <RetrievalPanel output={output} />;
    }
    if (stepNo === 4 && threats) {
      const output = stepOutput(4) as ThreatGenOutput | null;
      return (
        <ThreatTable
          data={threats}
          documents={documents}
          componentNames={componentNames}
          note={output?.llm_note}
        />
      );
    }
    if (stepNo === 5 && threats) {
      const output = stepOutput(5) as ValidationOutput | null;
      if (!output) return undefined;
      return (
        <div className="space-y-4">
          <ValidationSummary output={output} />
          <ThreatTable
            data={threats}
            documents={documents}
            componentNames={componentNames}
          />
        </div>
      );
    }
    if (stepNo === 6 && threats) {
      const output = stepOutput(6) as RiskOutput | null;
      if (!output) return undefined;
      return (
        <div className="space-y-4">
          <RiskSummary output={output} />
          <ThreatTable
            data={threats}
            documents={documents}
            componentNames={componentNames}
          />
        </div>
      );
    }
    if (stepNo === 8 && threats) {
      return (
        <ThreatTable
          data={threats}
          documents={documents}
          componentNames={componentNames}
          review={{
            readOnly,
            busy,
            onDecide: decide,
            onBulk: decideBulk,
          }}
        />
      );
    }
    if (stepNo === 9) {
      const output = stepOutput(9) as ReportOutput | null;
      if (output?.files) {
        return <ReportPanel runId={runId!} output={output} />;
      }
    }
    if (stepNo === 7 && threats) {
      const output = stepOutput(7) as MitigationOutput | null;
      if (!output) return undefined;
      return (
        <div className="space-y-4">
          <MitigationSummary output={output} />
          <ThreatTable
            data={threats}
            documents={documents}
            componentNames={componentNames}
          />
        </div>
      );
    }
    return undefined;
  };

  if (!runId) return null;

  return (
    <>
      <RunTopStrip
        run={stream.run}
        projectName={stream.run?.project_name ?? "Analiz yükleniyor"}
        status={stream.status}
        llm={stream.llm}
        onRestart={() => retry(1)}
        busy={busy}
        readOnly={readOnly}
      />

      {stream.error ? (
        <Card>
          <CardContent className="flex items-center gap-2 pt-5 text-sm text-level-critical">
            <AlertCircle className="h-4 w-4" aria-hidden />
            {stream.error}
          </CardContent>
        </Card>
      ) : null}

      {stream.placeholder ? (
        <div className="flex items-center gap-2 rounded-md border border-dashed border-border bg-surface px-3 py-2 text-xs text-muted-foreground">
          <Badge variant="warning">Örnek veri</Badge>
          1–7. adımlar gerçek dokümanı işler. 8. ve 9. adımlar henüz örnek
          veri üretir; gerçek çıktı Aşama 4&apos;te gelecek.
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
        <Card className="h-fit p-2">
          {metaLoading || definitions.length === 0 ? (
            <div className="space-y-2 p-2">
              {Array.from({ length: 9 }).map((_, index) => (
                <Skeleton key={index} className="h-14 w-full" />
              ))}
            </div>
          ) : (
            <Stepper
              definitions={definitions}
              steps={stream.steps}
              selected={selected}
              onSelect={(no) => {
                setSelected(no);
                setPinned(true);
              }}
              modelApprovalAfterStep={meta?.model_approval_after_step ?? 2}
              pauseStep={stream.pause?.step ?? null}
            />
          )}
        </Card>

        <div className="min-w-0 space-y-5">
          <StepDetail
            definition={definition}
            step={step}
            paused={pausedHere}
            pauseReason={stream.pause?.reason ?? null}
            onResume={resume}
            onRetry={() => retry(selected ?? 1)}
            busy={busy}
            readOnly={readOnly}
            buildPhase={meta?.build_phase ?? 0}
            content={panelFor(selected)}
          />
        </div>
      </div>

      <EventLog events={stream.events} connected={stream.connected} />
    </>
  );
}
