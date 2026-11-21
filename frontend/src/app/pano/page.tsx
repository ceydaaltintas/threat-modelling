"use client";

import { CircleHelp, ExternalLink, LayoutDashboard } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";
import { LEVELS, levelClasses, levelForScore, type Level } from "@/lib/levels";
import { STRIDE_SHORT, REVIEW_LABELS } from "@/lib/threats";
import type { DashboardData, DashboardRun } from "@/lib/types";
import { cn } from "@/lib/utils";

const SCALE = [1, 2, 3, 4, 5];

export default function DashboardPage() {
  const [runs, setRuns] = React.useState<DashboardRun[]>([]);
  const [runId, setRunId] = React.useState<string>("");
  const [data, setData] = React.useState<DashboardData | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [cellFilter, setCellFilter] = React.useState<string | null>(null);

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
  const maxCell = Math.max(1, ...Object.values(data?.heatmap ?? {}));

  const filteredTop = React.useMemo(() => {
    if (!data?.top_threats) return [];
    return data.top_threats;
  }, [data]);

  return (
    <>
      <PageHeader
        title="Özet panosu"
        description="Tamamlanan bir analizin tehdit dağılımı, risk ısı haritası ve en kritik bulguları."
        actions={
          runs.length > 0 ? (
            <select
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
              aria-label="Analiz seç"
              className="h-9 max-w-[320px] rounded-md border border-input bg-surface px-2 text-sm"
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.project} · {formatDateTime(run.created_at)} ·{" "}
                  {run.threats} tehdit
                </option>
              ))}
            </select>
          ) : null
        }
      />

      {error ? (
        <Card>
          <CardContent className="pt-5 text-sm text-level-critical">{error}</CardContent>
        </Card>
      ) : data === null ? (
        <SkeletonRows rows={5} />
      ) : !data.available ? (
        <EmptyState
          icon={LayoutDashboard}
          title="Gösterilecek analiz yok"
          description={data.reason ?? "Önce bir analiz çalıştırın."}
          action={
            <Link href="/analiz/yeni">
              <Badge variant="accent">Yeni analiz başlat</Badge>
            </Link>
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">{data.run?.project}</span>
            <Badge variant="outline">
              {data.kpis?.components} bileşen · {data.kpis?.flows} akış
            </Badge>
            {data.run?.id ? (
              <Link
                href={`/analiz/${data.run.id}`}
                className="flex items-center gap-1 text-xs text-accent hover:underline"
              >
                Analizi aç <ExternalLink className="h-3 w-3" aria-hidden />
              </Link>
            ) : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi label="Rapora dahil tehdit" value={data.kpis?.included ?? 0} />
            <Kpi
              label="Kritik"
              value={data.kpis?.critical ?? 0}
              tone="Kritik"
            />
            <Kpi label="Yüksek" value={data.kpis?.high ?? 0} tone="Yüksek" />
            <Kpi
              label="Karar verilen"
              value={`%${Math.round((data.kpis?.decided_ratio ?? 0) * 100)}`}
              hint={`${data.kpis?.decided ?? 0} / ${data.kpis?.total ?? 0}`}
            />
          </div>

          <div className="grid gap-5 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">5×5 risk ısı haritası</CardTitle>
                <CardDescription>
                  Eşikler: ≤{thresholds.low} Düşük, ≤{thresholds.medium} Orta,
                  ≤{thresholds.high} Yüksek, üzeri Kritik. Hücreye tıklayınca
                  tehdit tablosu o skorla filtrelenir.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <div className="flex flex-col justify-between py-1 text-[10px] text-muted-foreground">
                    {[...SCALE].reverse().map((value) => (
                      <span key={value} className="h-10 leading-10">
                        {value}
                      </span>
                    ))}
                  </div>
                  <div className="flex-1">
                    <div className="grid grid-cols-5 gap-1">
                      {[...SCALE].reverse().map((impact) =>
                        SCALE.map((likelihood) => {
                          const key = `${likelihood}x${impact}`;
                          const count = data.heatmap?.[key] ?? 0;
                          const score = impact * likelihood;
                          const level = levelForScore(score, thresholds);
                          return (
                            <button
                              key={key}
                              type="button"
                              disabled={count === 0}
                              onClick={() =>
                                setCellFilter(cellFilter === key ? null : key)
                              }
                              title={`Olasılık ${likelihood} × Etki ${impact} = ${score} (${level}) · ${count} tehdit`}
                              className={cn(
                                "flex h-10 items-center justify-center rounded border text-[11px] font-medium transition-opacity",
                                levelClasses[level],
                                count === 0 && "opacity-30",
                                cellFilter === key && "ring-2 ring-accent",
                              )}
                            >
                              {count || ""}
                            </button>
                          );
                        }),
                      )}
                    </div>
                    <div className="mt-1 grid grid-cols-5 gap-1 text-center text-[10px] text-muted-foreground">
                      {SCALE.map((value) => (
                        <span key={value}>{value}</span>
                      ))}
                    </div>
                    <p className="mt-1 text-center text-[10px] text-muted-foreground">
                      Olasılık → (dikey: etki)
                    </p>
                  </div>
                </div>
                {cellFilter && data.run?.id ? (
                  <Link
                    href={`/analiz/${data.run.id}`}
                    className="mt-3 block text-xs text-accent hover:underline"
                  >
                    {data.heatmap?.[cellFilter]} tehdidi analiz ekranında aç
                  </Link>
                ) : null}
              </CardContent>
            </Card>

            <div className="space-y-5">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Seviye ve durum dağılımı</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {LEVELS.map((level) => (
                      <Badge
                        key={level}
                        className={cn("border", levelClasses[level])}
                      >
                        {formatNumber(data.by_level?.[level] ?? 0)} {level}
                      </Badge>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(data.by_review ?? {}).map(([status, count]) => (
                      <Badge key={status} variant="outline">
                        {count} {REVIEW_LABELS[status] ?? status}
                      </Badge>
                    ))}
                  </div>
                  {data.kpis?.assumptions || data.kpis?.flagged ? (
                    <p className="text-xs text-muted-foreground">
                      {data.kpis?.assumptions} bulgu kanıtsız (varsayım),{" "}
                      {data.kpis?.flagged} bulgu otomatik doğrulamada
                      işaretlendi.
                    </p>
                  ) : null}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">STRIDE dağılımı</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1.5">
                  {Object.keys(STRIDE_SHORT).map((code) => {
                    const count = data.by_stride?.[code] ?? 0;
                    const total = Math.max(
                      1,
                      ...Object.values(data.by_stride ?? {}),
                    );
                    return (
                      <div key={code} className="flex items-center gap-2 text-xs">
                        <span className="w-32 shrink-0 text-muted-foreground">
                          {code} · {STRIDE_SHORT[code]}
                        </span>
                        <span className="h-3 flex-1 overflow-hidden rounded bg-muted">
                          <span
                            className="block h-full bg-accent"
                            style={{ width: `${(count / total) * 100}%` }}
                          />
                        </span>
                        <span className="w-6 text-right tabular-nums">{count}</span>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">En kritik 5 tehdit</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-2 text-xs">
                  {filteredTop.map((threat, index) => (
                    <li key={threat.id} className="flex items-start gap-2">
                      <span className="w-4 shrink-0 text-muted-foreground">
                        {index + 1}.
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-medium">{threat.title}</span>
                        <span className="text-muted-foreground">
                          {threat.component} · {threat.stride}
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
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Bileşen bazlı tehdit sayısı</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1.5">
                {(data.by_component ?? []).map(([name, count]) => {
                  const max = Math.max(
                    1,
                    ...(data.by_component ?? []).map(([, value]) => value),
                  );
                  return (
                    <div key={name} className="flex items-center gap-2 text-xs">
                      <span className="w-40 shrink-0 truncate text-muted-foreground">
                        {name}
                      </span>
                      <span className="h-3 flex-1 overflow-hidden rounded bg-muted">
                        <span
                          className="block h-full bg-primary/70"
                          style={{ width: `${(count / max) * 100}%` }}
                        />
                      </span>
                      <span className="w-6 text-right tabular-nums">{count}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <CircleHelp className="h-4 w-4 text-level-medium" aria-hidden />
                Dokümanda belirtilmeyen ama önemli konular
              </CardTitle>
              <CardDescription>
                Mimari dokümanın yanıtlamadığı, tehdit modellemesi için önemli
                sorular.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {(data.unknowns ?? []).length === 0 ? (
                <p className="text-xs text-muted-foreground">Kayıt yok.</p>
              ) : (
                <ul className="space-y-1.5 text-xs">
                  {data.unknowns?.map((item, index) => (
                    <li key={index} className="flex gap-2">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground" />
                      <span>
                        {item.text}
                        {item.impact ? (
                          <span className="block text-muted-foreground">
                            Önemi: {item.impact}
                          </span>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </>
  );
}

function Kpi({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: Level;
}) {
  return (
    <Card className={tone ? cn("border", levelClasses[tone]) : undefined}>
      <CardContent className="pt-5">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
        {hint ? (
          <p className="mt-0.5 text-[11px] text-muted-foreground">{hint}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
