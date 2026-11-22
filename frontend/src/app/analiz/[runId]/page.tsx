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
import { ThreatList } from "@/components/analysis/threat-list";
import { RunTopStrip } from "@/components/analysis/run-topstrip";
import { StepDetail } from "@/components/analysis/step-detail";
import { StepRail } from "@/components/analysis/step-rail";
import { SystemModelPanel } from "@/components/analysis/system-model-panel";
import { useRunStream } from "@/components/analysis/use-run-stream";
import { useMeta } from "@/components/providers/meta-provider";
import { useRole } from "@/components/providers/role-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
    // Review is not mandatory - undecided threats keep the system score and
    // the report says so. Sailing past the whole review in one click with no
    // word about it is another matter, so say what is being skipped.
    if (stream.pause?.reason === "expert_review") {
      const counters = stream.steps.find((item) => item.step_no === 8)?.counters;
      const pending = Number(counters?.pending ?? 0);
      const decided = Number(counters?.decided ?? 0);
      if (
        pending > 0 &&
        !window.confirm(
          (decided === 0
            ? `Hiçbir tehdit için uzman kararı vermediniz. ${pending} bulgu`
            : `${pending} bulgu için karar vermediniz; bunlar`) +
            " sistem puanıyla raporlanacak ve raporda \u201cuzman kararı" +
            " verilmedi\u201d olarak geçecek. Devam edilsin mi?",
        )
      )
        return;
    }
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

  const cancel = async () => {
    if (!runId) return;
    // Stopping loses the steps that have not run yet, so ask first.
    if (
      !window.confirm(
        "Analiz durdurulsun mu? Tamamlanan adımlar kalır; kalan adımlar " +
          "çalışmaz. Daha sonra kaldığı adımdan yeniden başlatabilirsiniz.",
      )
    )
      return;
    setBusy(true);
    try {
      await api.cancelRun(runId);
      stream.reload();
      toast({ title: "Analiz durduruldu", tone: "success" });
    } catch (err) {
      toast({
        title: "Analiz durdurulamadı",
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
        // The step 8 counters live on the run row; keep them honest.
        await stream.refreshSteps();
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
    [runId, reloadThreats, toast, stream],
  );

  const decideBulk = React.useCallback(
    async (
      threatIds: string[],
      action: "accept" | "reject" | "false_positive" | "reset",
      note?: string,
    ) => {
      if (!runId) return;
      setBusy(true);
      try {
        const result = await api.reviewBulk(runId, {
          threat_ids: threatIds,
          action,
          note: note?.trim() || undefined,
        });
        await reloadThreats();
        await stream.refreshSteps();
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
    [runId, reloadThreats, toast, stream],
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
    // Never show a step's output before that step has run: the data would
    // belong to an earlier state of the pipeline, and step 8 would offer
    // decisions on threats whose risk and mitigations are not final.
    if (stepNo === null) return undefined;
    const own = stream.steps.find((item) => item.step_no === stepNo);
    if (!own || own.status === "pending") return undefined;

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
        <ThreatList
          data={threats}
          documents={documents}
          componentNames={componentNames}
          note={output?.llm_note}
          step={4}
        />
      );
    }
    if (stepNo === 5 && threats) {
      const output = stepOutput(5) as ValidationOutput | null;
      if (!output) return undefined;
      return (
        <div className="space-y-4">
          <ValidationSummary output={output} />
          <ThreatList
            data={threats}
            documents={documents}
            componentNames={componentNames}
            step={5}
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
          <ThreatList
            data={threats}
            documents={documents}
            componentNames={componentNames}
            step={6}
          />
        </div>
      );
    }
    if (stepNo === 8 && threats) {
      // Once step 9 has written the report, a new decision would make the
      // downloaded files wrong without saying so. Re-running step 8 is the
      // way through: it marks the report stale and regenerates it.
      const reportWritten = stepStatus(9) === "done";
      return (
        <div className="space-y-3">
          {reportWritten ? (
            <div className="flex flex-wrap items-center gap-3 rounded-md border border-border bg-surface-muted p-3">
              <p className="min-w-0 flex-1 text-xs text-muted-foreground">
                Rapor üretildi, kararlar dosyalara yazıldı. Karar değiştirmek
                için 8. adımı yeniden çalıştırın; rapor da yenilenir.
              </p>
              <Button
                variant="outline"
                size="sm"
                disabled={busy || readOnly}
                onClick={() => retry(8)}
              >
                8. adımı yeniden çalıştır
              </Button>
            </div>
          ) : null}
          <ThreatList
            data={threats}
            documents={documents}
            componentNames={componentNames}
            step={8}
            review={{
              readOnly: readOnly || reportWritten,
              readOnlyReason:
                !readOnly && reportWritten
                  ? "Rapor üretildi; karar değiştirmek için 8. adımı yeniden çalıştırın."
                  : undefined,
              busy,
              onDecide: decide,
              onBulk: decideBulk,
            }}
          />
        </div>
      );
    }
    if (stepNo === 9) {
      const output = stepOutput(9) as ReportOutput | null;
      if (output?.files) {
        return (
          <ReportPanel
            runId={runId!}
            output={output}
            findings={
              threats ? (
                <ThreatList
                  data={threats}
                  documents={documents}
                  componentNames={componentNames}
                />
              ) : undefined
            }
          />
        );
      }
    }
    if (stepNo === 7 && threats) {
      const output = stepOutput(7) as MitigationOutput | null;
      if (!output) return undefined;
      return (
        <div className="space-y-4">
          <MitigationSummary output={output} />
          <ThreatList
            data={threats}
            documents={documents}
            componentNames={componentNames}
            step={7}
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
        onCancel={cancel}
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

      {metaLoading || definitions.length === 0 ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <StepRail
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

      <StepDetail
        definition={definition}
        step={step}
        paused={pausedHere}
        pauseReason={stream.pause?.reason ?? null}
        onResume={resume}
        onRetry={() => retry(selected ?? 1)}
        busy={busy}
        readOnly={readOnly}
        content={panelFor(selected)}
      />

      <EventLog events={stream.events} connected={stream.connected} />
    </>
  );
}
