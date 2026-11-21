"use client";

import {
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatBytes, formatNumber } from "@/lib/format";
import { levelClasses, type Level } from "@/lib/levels";
import type { ReportOutput } from "@/lib/types";
import { cn } from "@/lib/utils";

const FILE_META: Record<
  string,
  { icon: LucideIcon; label: string; description: string }
> = {
  pdf: {
    icon: FileText,
    label: "PDF yönetici raporu",
    description: "Yönetime sunulacak özet rapor.",
  },
  excel: {
    icon: FileSpreadsheet,
    label: "Excel tehdit listesi",
    description: "Tüm tehditler, kanıt, kaynak ve kararlarla birlikte.",
  },
  json: {
    icon: FileJson,
    label: "JSON (tam veri)",
    description: "Risk kırılımı ve doğrulama notları dahil her şey.",
  },
  otm: {
    icon: FileJson,
    label: "JSON (Open Threat Model)",
    description:
      "Diğer araçlara aktarım için. Eşleme yaklaşıktır; kanıt ve risk kırılımı OTM'de yer almaz.",
  },
};

/**
 * Step 9 panel.
 *
 * The findings themselves are shown here, in the product. Downloading a file
 * is for sending the result to someone else, never a precondition for
 * reading it.
 */
export function ReportPanel({
  runId,
  output,
  findings,
}: {
  runId: string;
  output: ReportOutput;
  /** The full findings list, rendered read-only under the summary. */
  findings?: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle className="text-sm">Yönetici özeti</CardTitle>
              <CardDescription>
                Raporun ilk sayfasında yer alan özet.
              </CardDescription>
            </div>
            {output.summary_is_ai ? (
              <Badge variant="accent">
                <Sparkles className="h-3 w-3" aria-hidden /> AI üretti
              </Badge>
            ) : (
              <Badge variant="default">Sistem üretti</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="whitespace-pre-line rounded-md bg-surface-muted p-3 text-sm leading-relaxed">
            {output.summary_text ?? "—"}
          </p>
          {output.summary_is_ai ? (
            <p className="text-[11px] text-muted-foreground">
              Bu özet yapay zekâ ile taslaklanmıştır; yayımlamadan önce
              gözden geçirilmelidir. Raporda da aynı etiketle yer alır.
            </p>
          ) : (
            <p className="text-[11px] text-muted-foreground">
              LLM sağlayıcısı kullanılamadığı için özet, hesaplanan sayılardan
              doğrudan üretildi.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Rapordaki sayılar</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {(["Kritik", "Yüksek", "Orta", "Düşük"] as Level[]).map((level) => (
                <Badge key={level} className={cn("border", levelClasses[level])}>
                  {formatNumber(output.by_level[level] ?? 0)} {level}
                </Badge>
              ))}
            </div>
            <dl className="grid grid-cols-2 gap-2 text-xs">
              {[
                ["Toplam bulgu", output.counts.total],
                ["Rapora dahil", output.counts.included],
                ["Uzmanın elediği", output.counts.excluded],
                ["Varsayım", output.counts.assumptions],
                ["Doğrulamada işaretli", output.counts.flagged],
                ["Karar bekleyen", output.counts.pending],
              ].map(([label, value]) => (
                <div key={String(label)} className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">{label}</dt>
                  <dd className="tabular-nums">{formatNumber(Number(value))}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">En kritik 5 bulgu</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-1.5 text-xs">
              {output.top_threats.map((threat, index) => (
                <li key={threat.id} className="flex items-start gap-2">
                  <span className="w-4 shrink-0 text-muted-foreground">
                    {index + 1}.
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">
                      {threat.title}
                    </span>
                    <span className="text-muted-foreground">
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
              {output.top_threats.length === 0 ? (
                <li className="text-muted-foreground">Kayıt yok.</li>
              ) : null}
            </ol>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Dışarı paylaşmak için dosyalar</CardTitle>
          <CardDescription>
            Bulguların tamamı aşağıda ekranda. Bu dosyalar yalnızca raporu
            kurum dışına ya da toplantıya götürmek içindir; dosyalar bu
            bilgisayarda üretildi, indirme dışarı veri göndermez.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {output.files.map((file) => {
            const meta = FILE_META[file.kind] ?? {
              icon: FileJson,
              label: file.name,
              description: "",
            };
            const Icon = meta.icon;
            return (
              <div
                key={file.name}
                className="flex items-start justify-between gap-3 rounded-md border border-border p-3"
              >
                <div className="flex min-w-0 items-start gap-2.5">
                  <Icon className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
                  <div className="min-w-0">
                    <p className="text-xs font-medium">{meta.label}</p>
                    <p className="text-[11px] text-muted-foreground">
                      {meta.description}
                    </p>
                    <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                      {file.name} · {formatBytes(file.size)}
                    </p>
                  </div>
                </div>
                <a
                  href={api.reportUrl(runId, file.name)}
                  download={file.name}
                  className="shrink-0"
                >
                  <Button variant="outline" size="sm">
                    <Download aria-hidden /> İndir
                  </Button>
                </a>
              </div>
            );
          })}
        </CardContent>
      </Card>


      {findings ? (
        <section className="space-y-2">
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold">Rapordaki tüm bulgular</h3>
            <span className="text-[11px] text-muted-foreground">
              Bir satıra tıklayın: kanıt, risk kırılımı ve önlemler açılır.
            </span>
          </div>
          {findings}
        </section>
      ) : null}
    </div>
  );
}
