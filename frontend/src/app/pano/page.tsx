"use client";

import { ExternalLink, LayoutDashboard } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";
import { LEVELS, levelClasses, levelForScore, type Level } from "@/lib/levels";
import { REVIEW_LABELS, STRIDE_SHORT } from "@/lib/threats";
import type { DashboardData, DashboardRun } from "@/lib/types";
import { cn } from "@/lib/utils";

const SCALE = [1, 2, 3, 4, 5];

/** One analysis, summarised for someone who will not open the detail. */
export default function DashboardPage() {
  const [runs, setRuns] = React.useState<DashboardRun[]>([]);
  const [runId, setRunId] = React.useState("");
  const [data, setData] = React.useState<DashboardData | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api.dashboardRuns().then(setRuns).catch(() => setRuns([]));
  }, []);

  React.useEffect(() => {
    setData(null);
    api
      .dashboard(runId || undefined)
      .then((value) => {
        setData(value);
        setError(null);
        if (!runId && value.run?.id) setRunId(value.run.id);
      })
      .catch((err: Error) => setError(err.message));
  }, [runId]);

  const thresholds = data?.thresholds ?? { low: 4, medium: 9, high: 16 };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-5 py-2">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Özet panosu</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {data?.run?.project ?? "Bir analizin özeti."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {runs.length > 0 ? (
            <select
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
              aria-label="Analiz seç"
              className="h-9 max-w-[300px] rounded-md border border-input bg-surface px-2 text-sm"
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.project} · {formatDateTime(run.created_at)}
                </option>
              ))}
            </select>
          ) : null}
          {data?.run?.id ? (
            <Link
              href={`/analiz/${data.run.id}`}
              className="flex items-center gap-1 text-xs text-accent hover:underline"
            >
              Analizi aç <ExternalLink className="h-3 w-3" aria-hidden />
            </Link>
          ) : null}
        </div>
      </div>

      {error ? (
        <p className="rounded-md border border-level-critical/40 bg-level-critical/10 p-3 text-sm text-level-critical">
          {error}
        </p>
      ) : data === null ? (
        <SkeletonRows rows={5} />
      ) : !data.available ? (
        <EmptyState
          icon={LayoutDashboard}
          title="Gösterilecek analiz yok"
          description={data.reason ?? "Önce bir analiz çalıştırın."}
          action={
            <Link href="/analiz/yeni" className="text-sm text-accent hover:underline">
              Yeni analiz başlat
            </Link>
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap items-stretch gap-2">
            {LEVELS.map((level) => (
              <div
                key={level}
                className={cn(
                  "min-w-[96px] flex-1 rounded-md border px-3 py-2",
                  levelClasses[level],
                )}
              >
                <p className="text-xl font-semibold tabular-nums leading-none">
                  {formatNumber(data.by_level?.[level] ?? 0)}
                </p>
                <p className="mt-1 text-[11px]">{level}</p>
              </div>
            ))}
            <div className="min-w-[96px] flex-1 rounded-md border border-border px-3 py-2">
              <p className="text-xl font-semibold tabular-nums leading-none">
                %{Math.round((data.kpis?.decided_ratio ?? 0) * 100)}
              </p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                karar verildi
              </p>
            </div>
            <div className="min-w-[96px] flex-1 rounded-md border border-border px-3 py-2">
              <p className="text-xl font-semibold tabular-nums leading-none">
                {data.kpis?.components}
              </p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                bileşen · {data.kpis?.flows} akış
              </p>
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
            <section>
              <h2 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Risk ısı haritası
              </h2>
              <div className="flex gap-1.5 rounded-md border border-border bg-surface p-3">
                <div className="flex flex-col justify-between py-0.5 text-[10px] text-muted-foreground">
                  {[...SCALE].reverse().map((value) => (
                    <span key={value} className="h-9 leading-9">
                      {value}
                    </span>
                  ))}
                </div>
                <div className="flex-1">
                  <div className="grid grid-cols-5 gap-1">
                    {[...SCALE].reverse().map((impact) =>
                      SCALE.map((likelihood) => {
                        const count =
                          data.heatmap?.[`${likelihood}x${impact}`] ?? 0;
                        const level = levelForScore(impact * likelihood, thresholds);
                        return (
                          <div
                            key={`${impact}-${likelihood}`}
                            title={`Olasılık ${likelihood} × Etki ${impact} = ${impact * likelihood} (${level}) · ${count} tehdit`}
                            className={cn(
                              "flex h-9 items-center justify-center rounded border text-[11px] font-medium",
                              levelClasses[level],
                              count === 0 && "opacity-30",
                            )}
                          >
                            {count || ""}
                          </div>
                        );
                      }),
                    )}
                  </div>
                  <div className="mt-1 grid grid-cols-5 gap-1 text-center text-[10px] text-muted-foreground">
                    {SCALE.map((value) => (
                      <span key={value}>{value}</span>
                    ))}
                  </div>
                  <p className="mt-0.5 text-center text-[10px] text-muted-foreground">
                    olasılık → · dikey: etki
                  </p>
                </div>
              </div>
            </section>

            <section>
              <h2 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                En kritik 5 bulgu
              </h2>
              <ol className="space-y-1">
                {(data.top_threats ?? []).map((threat, index) => (
                  <li
                    key={threat.id}
                    className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm"
                  >
                    <span className="w-4 shrink-0 text-xs text-muted-foreground">
                      {index + 1}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate">{threat.title}</span>
                      <span className="block truncate text-[11px] text-muted-foreground">
                        {threat.component}
                      </span>
                    </span>
                    <Badge
                      className={cn("border", levelClasses[threat.level as Level])}
                    >
                      {threat.score}
                    </Badge>
                  </li>
                ))}
              </ol>
            </section>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Bars
              title="STRIDE dağılımı"
              rows={Object.keys(STRIDE_SHORT).map((code) => [
                `${code} · ${STRIDE_SHORT[code]}`,
                data.by_stride?.[code] ?? 0,
              ])}
            />
            <Bars
              title="Bileşen bazlı"
              rows={(data.by_component ?? []).map(([name, count]) => [name, count])}
            />
          </div>

          <section>
            <h2 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Durum ve açık konular
            </h2>
            <div className="space-y-2 rounded-md border border-border bg-surface p-3">
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(data.by_review ?? {}).map(([status, count]) => (
                  <Badge key={status} variant="outline">
                    {count} {REVIEW_LABELS[status] ?? status}
                  </Badge>
                ))}
                {data.kpis?.assumptions ? (
                  <Badge variant="warning">
                    {data.kpis.assumptions} kanıtsız
                  </Badge>
                ) : null}
              </div>
              {(data.unknowns ?? []).length > 0 ? (
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {data.unknowns?.map((item, index) => (
                    <li key={index} className="flex gap-2">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground" />
                      <span>{item.text}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Dokümanda belirtilmeyen konu kaydedilmedi.
                </p>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function Bars({
  title,
  rows,
}: {
  title: string;
  rows: Array<[string, number]>;
}) {
  const max = Math.max(1, ...rows.map(([, value]) => value));
  return (
    <section>
      <h2 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      <div className="space-y-1.5 rounded-md border border-border bg-surface p-3">
        {rows.map(([label, count]) => (
          <div key={label} className="flex items-center gap-2 text-xs">
            <span className="w-36 shrink-0 truncate text-muted-foreground">
              {label}
            </span>
            <span className="h-2.5 flex-1 overflow-hidden rounded bg-muted">
              <span
                className="block h-full rounded bg-accent"
                style={{ width: `${(count / max) * 100}%` }}
              />
            </span>
            <span className="w-6 text-right tabular-nums">{count}</span>
          </div>
        ))}
        {rows.length === 0 ? (
          <p className="text-xs text-muted-foreground">Kayıt yok.</p>
        ) : null}
      </div>
    </section>
  );
}
