"use client";

import { ChevronRight, ListChecks, PlusCircle } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ProjectRow } from "@/lib/types";

const RUN_STATUS_LABEL: Record<string, string> = {
  pending: "Başlatılıyor",
  running: "Çalışıyor",
  waiting_user: "Kullanıcı bekleniyor",
  done: "Tamamlandı",
  failed: "Hata",
  cancelled: "İptal edildi",
};

/** The only colour in a row: one dot, so the status column stays readable. */
const DOT: Record<string, string> = {
  none: "bg-border",
  pending: "bg-muted-foreground/50",
  running: "bg-accent animate-pulse",
  waiting_user: "bg-level-high",
  done: "bg-level-low",
  failed: "bg-level-critical",
  cancelled: "bg-muted-foreground/50",
};

export default function ProjectsPage() {
  const [projects, setProjects] = React.useState<ProjectRow[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api
      .projects()
      .then(setProjects)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="mx-auto w-full max-w-4xl space-y-4 py-2">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Projeler</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Her satır bir mimari dokümandan üretilmiş analizdir.
          </p>
        </div>
        <Link href="/analiz/yeni">
          <Button>
            <PlusCircle aria-hidden /> Yeni analiz
          </Button>
        </Link>
      </div>

      {error ? (
        <p className="rounded-md border border-level-critical/40 bg-level-critical/10 p-3 text-sm text-level-critical">
          {error}
        </p>
      ) : projects === null ? (
        <SkeletonRows rows={4} />
      ) : projects.length === 0 ? (
        <EmptyState
          icon={ListChecks}
          title="Henüz analiz yok"
          description="Bir mimari doküman yükleyerek ilk analizi başlatın."
          action={
            <Link href="/analiz/yeni">
              <Button>
                <PlusCircle aria-hidden /> Yeni analiz başlat
              </Button>
            </Link>
          }
        />
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface">
          {projects.map((project) => {
            const status = project.last_run?.status;
            const critical = project.risk_summary.critical;
            const high = project.risk_summary.high;
            // Risk is a number, not a decoration: one quiet line in its own
            // column, so every row reads at the same place.
            const risk =
              critical || high
                ? [
                    critical ? `${critical} kritik` : null,
                    high ? `${high} yüksek` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")
                : "—";
            const row = (
              <>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {project.name}
                  </span>
                  <span className="block text-[11px] text-muted-foreground">
                    {formatDateTime(
                      project.last_run?.started_at ?? project.created_at,
                    )}
                    {project.sample_key ? " · örnek doküman" : ""}
                  </span>
                </span>
                <span className="hidden w-32 shrink-0 text-right text-xs tabular-nums text-muted-foreground sm:block">
                  {risk}
                </span>
                <span className="flex w-36 shrink-0 items-center justify-end gap-1.5 text-xs">
                  <span
                    className={cn("h-1.5 w-1.5 rounded-full", DOT[status ?? "none"])}
                    aria-hidden
                  />
                  <span className="truncate text-muted-foreground">
                    {status ? RUN_STATUS_LABEL[status] ?? status : "Analiz yok"}
                  </span>
                </span>
                <ChevronRight
                  className={cn(
                    "h-4 w-4 shrink-0 text-muted-foreground",
                    !project.last_run && "invisible",
                  )}
                  aria-hidden
                />
              </>
            );
            return (
              <li key={project.id}>
                {project.last_run ? (
                  <Link
                    href={`/analiz/${project.last_run.id}`}
                    className="flex items-center gap-3 px-3 py-2.5 transition-colors hover:bg-surface-muted"
                  >
                    {row}
                  </Link>
                ) : (
                  <div className="flex items-center gap-3 px-3 py-2.5">{row}</div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
