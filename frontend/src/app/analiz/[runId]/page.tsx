"use client";

import { AlertCircle } from "lucide-react";
import { useParams } from "next/navigation";
import * as React from "react";

import { EventLog } from "@/components/analysis/event-log";
import { RunTopStrip } from "@/components/analysis/run-topstrip";
import { StepDetail } from "@/components/analysis/step-detail";
import { Stepper } from "@/components/analysis/stepper";
import { useRunStream } from "@/components/analysis/use-run-stream";
import { useMeta } from "@/components/providers/meta-provider";
import { useRole } from "@/components/providers/role-provider";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";

export default function AnalysisPage() {
  const params = useParams<{ runId: string }>();
  const runId = params?.runId ?? null;
  const { meta, loading: metaLoading } = useMeta();
  const { readOnly } = useRole();
  const { toast } = useToast();

  const stream = useRunStream(runId);
  const [selected, setSelected] = React.useState<number | null>(null);
  const [busy, setBusy] = React.useState(false);

  // Follow the active step until the user clicks another one.
  const [pinned, setPinned] = React.useState(false);
  React.useEffect(() => {
    if (pinned) return;
    const active =
      stream.steps.find((step) => step.status === "running") ??
      stream.steps.find((step) => step.status === "waiting_user") ??
      [...stream.steps].reverse().find((step) => step.status === "done");
    if (active) setSelected(active.step_no);
  }, [stream.steps, pinned]);

  const definitions = meta?.steps ?? [];
  const definition = definitions.find((item) => item.no === selected) ?? null;
  const step = stream.steps.find((item) => item.step_no === selected) ?? null;

  const pausedHere =
    stream.pause !== null && stream.pause.step === selected;

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

  const restart = async () => {
    toast({
      title: "Yeniden çalıştırma Aşama 1'de",
      description:
        "Gerçek işlem hattı bağlandığında bu düğme adımları baştan koşturacak.",
      tone: "info",
    });
  };

  const retryStep = async () => {
    toast({
      title: "Adım yeniden denemesi Aşama 1'de",
      description: "Her adım bağımsız olarak yeniden denenebilir olacak.",
      tone: "info",
    });
  };

  if (!runId) return null;

  return (
    <>
      <RunTopStrip
        run={stream.run}
        projectName={stream.run?.project_name ?? "Analiz yükleniyor"}
        status={stream.status}
        llm={stream.llm}
        onRestart={restart}
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
          Adım akışı, olay günlüğü ve duraklama noktaları gerçektir; adım
          çıktıları Aşama 0&apos;da örnek veridir.
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
            onRetry={retryStep}
            busy={busy}
            readOnly={readOnly}
            buildPhase={meta?.build_phase ?? 0}
          />
        </div>
      </div>

      <EventLog events={stream.events} connected={stream.connected} />
    </>
  );
}
