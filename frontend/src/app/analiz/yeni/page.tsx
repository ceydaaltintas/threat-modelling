"use client";

import { FileUp, Play, Sparkles, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { useMeta } from "@/components/providers/meta-provider";
import { useRole } from "@/components/providers/role-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import type { SampleScenario } from "@/lib/types";
import { cn } from "@/lib/utils";

const ACCEPTED = ".pdf,.docx,.md,.txt,.png,.jpg,.jpeg";

export default function NewAnalysisPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { meta } = useMeta();
  const { readOnly } = useRole();

  const [samples, setSamples] = React.useState<SampleScenario[] | null>(null);
  const [selectedSample, setSelectedSample] = React.useState<string | null>(null);
  const [files, setFiles] = React.useState<File[]>([]);
  const [dragging, setDragging] = React.useState(false);
  const [autoContinue, setAutoContinue] = React.useState(false);
  const [starting, setStarting] = React.useState(false);

  React.useEffect(() => {
    api
      .samples()
      .then(setSamples)
      .catch((err: Error) =>
        toast({ title: "Örnek senaryolar yüklenemedi", description: err.message, tone: "error" }),
      );
  }, [toast]);

  const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    const dropped = Array.from(event.dataTransfer.files);
    if (dropped.length > 0) {
      setFiles(dropped);
      setSelectedSample(null);
    }
  };

  const start = async () => {
    setStarting(true);
    try {
      const run = selectedSample
        ? await api.createRun({
            sample_key: selectedSample,
            auto_continue: autoContinue,
          })
        : await api.uploadRun(files, {
            project_name: files[0]?.name.replace(/\.[^.]+$/, "") || undefined,
            auto_continue: autoContinue,
          });
      router.push(`/analiz/${run.id}`);
    } catch (err) {
      toast({
        title: "Analiz başlatılamadı",
        description: (err as Error).message,
        tone: "error",
      });
      setStarting(false);
    }
  };

  const canStart = (selectedSample !== null || files.length > 0) && !readOnly;

  return (
    <>
      <PageHeader
        title="Yeni analiz"
        description="Doküman yükleyin veya örnek senaryo seçin."
      />

      <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Doküman yükle</CardTitle>
            <CardDescription>
              PDF, DOCX, MD, TXT, PNG/JPG · çoklu dosya
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={cn(
                "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
                dragging
                  ? "border-accent bg-accent-subtle"
                  : "border-border bg-surface-muted",
              )}
            >
              <UploadCloud className="h-7 w-7 text-muted-foreground" aria-hidden />
              <p className="text-sm font-medium">
                Dosyaları buraya sürükleyip bırakın
              </p>
              <p className="text-xs text-muted-foreground">veya</p>
              <label className="cursor-pointer">
                <span className="inline-flex h-9 items-center gap-2 rounded-md border border-input bg-surface px-4 text-sm hover:bg-surface-muted">
                  <FileUp className="h-4 w-4" aria-hidden /> Dosya seç
                </span>
                <input
                  type="file"
                  multiple
                  accept={ACCEPTED}
                  className="sr-only"
                  onChange={(event) => {
                    const picked = Array.from(event.target.files ?? []);
                    if (picked.length > 0) {
                      setFiles(picked);
                      setSelectedSample(null);
                    }
                  }}
                />
              </label>
            </div>

            {files.length > 0 ? (
              <ul className="space-y-1.5 text-sm">
                {files.map((file) => (
                  <li
                    key={file.name}
                    className="flex items-center justify-between rounded-md border border-border px-3 py-2"
                  >
                    <span className="truncate">{file.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatBytes(file.size)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}

            <p className="rounded-md bg-surface-muted p-3 text-xs text-muted-foreground">
              Yüklenen dosyalardan metin çıkarılır ve sistem modeli LLM ile
              oluşturulur. Dosyalar yalnızca bu bilgisayarda saklanır; gerçek
              banka verisi yüklemeyin.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Örnek senaryo seç</CardTitle>
            <CardDescription>
              Üç kurgusal banka dokümanı. Gerçek banka verisi içermezler.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {samples === null ? (
              <p className="text-sm text-muted-foreground">Yükleniyor…</p>
            ) : (
              samples.map((sample) => {
                const active = selectedSample === sample.key;
                return (
                  <button
                    key={sample.key}
                    type="button"
                    onClick={() => {
                      setSelectedSample(sample.key);
                      setFiles([]);
                    }}
                    aria-pressed={active}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left transition-colors",
                      active
                        ? "border-accent bg-accent-subtle"
                        : "border-border hover:bg-surface-muted",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium">{sample.title}</p>
                      <Badge variant="outline">{sample.doc_code}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {sample.summary}
                    </p>
                    <p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                      <Sparkles className="h-3 w-3" aria-hidden />
                      Vurgu: {sample.focus}
                      {sample.available ? (
                        <span>· {formatBytes(sample.size_bytes)}</span>
                      ) : (
                        <span className="text-level-critical">
                          · dosya bulunamadı
                        </span>
                      )}
                    </p>
                  </button>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ayar özeti</CardTitle>
          <CardDescription>
            Bu değerler ortam değişkenlerinden okunur; API anahtarı hiçbir ekranda
            gösterilmez.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <dl className="grid gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-muted-foreground">LLM sağlayıcı</dt>
              <dd>{meta?.llm_provider ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Model</dt>
              <dd>{meta?.llm_model || "README'den seçilecek"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">API anahtarı</dt>
              <dd>
                {meta?.llm_configured ? (
                  <Badge variant="success">Tanımlı</Badge>
                ) : (
                  <Badge variant="warning">Tanımsız</Badge>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Kayıtlı çıktı modu</dt>
              <dd>{meta?.demo_replay ?? "—"}</dd>
            </div>
          </dl>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoContinue}
              onChange={(event) => setAutoContinue(event.target.checked)}
              className="h-4 w-4 rounded border-input"
            />
            Otomatik devam (model onayı duraklamasını atla)
          </label>

          <div className="flex items-center gap-3">
            <Button onClick={start} disabled={!canStart || starting} size="lg">
              <Play aria-hidden /> {starting ? "Başlatılıyor…" : "Analizi başlat"}
            </Button>
            {readOnly ? (
              <p className="text-xs text-muted-foreground">
                Yönetici rolü salt okunurdur; analiz başlatmak için Güvenlik Uzmanı
                rolüne geçin.
              </p>
            ) : !canStart ? (
              <p className="text-xs text-muted-foreground">
                Devam etmek için bir dosya yükleyin veya örnek senaryo seçin.
              </p>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </>
  );
}
