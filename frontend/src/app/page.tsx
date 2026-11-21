"use client";

import { ListChecks, PlusCircle } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { ProjectRow } from "@/lib/types";

const RUN_STATUS_LABEL: Record<string, string> = {
  pending: "Başlatılıyor",
  running: "Çalışıyor",
  waiting_user: "Kullanıcı bekleniyor",
  done: "Tamamlandı",
  failed: "Hata",
  cancelled: "İptal edildi",
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
    <>
      <PageHeader
        title="Projeler"
        description="Her proje, bir mimari dokümandan üretilmiş bir tehdit modeli analizidir."
        actions={
          <Link href="/analiz/yeni">
            <Button>
              <PlusCircle aria-hidden /> Yeni analiz
            </Button>
          </Link>
        }
      />

      {error ? (
        <Card>
          <CardContent className="pt-5 text-sm text-level-critical">
            {error}
          </CardContent>
        </Card>
      ) : projects === null ? (
        <SkeletonRows rows={4} />
      ) : projects.length === 0 ? (
        <EmptyState
          icon={ListChecks}
          title="Henüz analiz yok"
          description="Bir mimari doküman yükleyerek ya da hazır örnek senaryolardan birini seçerek ilk analizi başlatın."
          action={
            <Link href="/analiz/yeni">
              <Button>
                <PlusCircle aria-hidden /> Yeni analiz başlat
              </Button>
            </Link>
          }
        />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-surface-muted text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Proje</th>
                  <th className="px-4 py-2.5 font-medium">Son analiz</th>
                  <th className="px-4 py-2.5 font-medium">Durum</th>
                  <th className="px-4 py-2.5 font-medium">Risk özeti</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {projects.map((project) => (
                  <tr
                    key={project.id}
                    className="border-b border-border last:border-0 hover:bg-surface-muted"
                  >
                    <td className="px-4 py-3">
                      <p className="font-medium">{project.name}</p>
                      {project.sample_key ? (
                        <p className="text-xs text-muted-foreground">
                          Örnek senaryo
                        </p>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDateTime(
                        project.last_run?.started_at ?? project.created_at,
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {project.last_run ? (
                        <Badge
                          variant={
                            project.last_run.status === "done"
                              ? "success"
                              : project.last_run.status === "failed"
                                ? "danger"
                                : "accent"
                          }
                        >
                          {RUN_STATUS_LABEL[project.last_run.status] ??
                            project.last_run.status}
                        </Badge>
                      ) : (
                        <Badge>Analiz yok</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex flex-wrap gap-1.5">
                        <Badge variant="danger">
                          {project.risk_summary.critical} Kritik
                        </Badge>
                        <Badge variant="warning">
                          {project.risk_summary.high} Yüksek
                        </Badge>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {project.last_run ? (
                        <Link
                          href={`/analiz/${project.last_run.id}`}
                          className="text-xs text-accent hover:underline"
                        >
                          Analizi aç
                        </Link>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}
