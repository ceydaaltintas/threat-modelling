"use client";

import { FileText, Loader2, Play, UploadCloud, X } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { useMeta } from "@/components/providers/meta-provider";
import { useRole } from "@/components/providers/role-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import type { SampleScenario } from "@/lib/types";
import { cn } from "@/lib/utils";

// Şema kaynakları da kabul edilir: kutu ve ok bilgisi oradan okunur.
const ACCEPTED = ".pdf,.docx,.drawio,.vsdx,.xml,.md,.txt,.png,.jpg,.jpeg";

/**
 * Starting an analysis is one action: give it a document.
 *
 * The bundled sample documents are a demo aid, not part of the product, so
 * they sit behind a quiet link instead of taking half the screen.
 */
export default function NewAnalysisPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { meta } = useMeta();
  const { readOnly } = useRole();

  const [files, setFiles] = React.useState<File[]>([]);
  const [dragging, setDragging] = React.useState(false);
  const [autoContinue, setAutoContinue] = React.useState(false);
  const [starting, setStarting] = React.useState(false);

  const [showSamples, setShowSamples] = React.useState(false);
  const [samples, setSamples] = React.useState<SampleScenario[] | null>(null);
  const [selectedSample, setSelectedSample] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!showSamples || samples) return;
    api.samples().then(setSamples).catch(() => setSamples([]));
  }, [showSamples, samples]);

  const addFiles = (incoming: File[]) => {
    if (incoming.length === 0) return;
    setFiles((current) => [...current, ...incoming]);
    setSelectedSample(null);
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

  const chosenSample = samples?.find((item) => item.key === selectedSample);
  const canStart = (files.length > 0 || selectedSample !== null) && !readOnly;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-5 py-2">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Yeni analiz</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Mimari dokümanı yükleyin; sistem modelini çıkarıp tehditleri üretelim.
        </p>
      </div>

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          addFiles(Array.from(event.dataTransfer.files));
        }}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors",
          dragging
            ? "border-accent bg-accent-subtle"
            : "border-border bg-surface hover:border-accent/40",
        )}
      >
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-muted">
          <UploadCloud className="h-6 w-6 text-accent" aria-hidden />
        </span>
        <div>
          <p className="text-sm font-medium">
            Dokümanı buraya sürükleyip bırakın
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            PDF, DOCX, MD, TXT, PNG, JPG · şema için DRAWIO, VSDX veya XML ·
            birden fazla dosya olabilir
          </p>
        </div>
        <label className="cursor-pointer">
          <span className="inline-flex h-9 items-center gap-2 rounded-md border border-input bg-surface px-4 text-sm font-medium hover:bg-surface-muted">
            Dosya seç
          </span>
          <input
            type="file"
            multiple
            accept={ACCEPTED}
            className="sr-only"
            onChange={(event) => addFiles(Array.from(event.target.files ?? []))}
          />
        </label>
      </div>

      {files.length > 0 ? (
        <ul className="space-y-1.5">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="flex items-center gap-2.5 rounded-md border border-border bg-surface px-3 py-2"
            >
              <FileText className="h-4 w-4 shrink-0 text-accent" aria-hidden />
              <span className="min-w-0 flex-1 truncate text-sm">{file.name}</span>
              <span className="shrink-0 text-xs text-muted-foreground">
                {formatBytes(file.size)}
              </span>
              <button
                type="button"
                onClick={() =>
                  setFiles((current) => current.filter((_, i) => i !== index))
                }
                aria-label={`${file.name} dosyasını kaldır`}
                className="rounded p-1 text-muted-foreground hover:bg-surface-muted hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {chosenSample ? (
        <div className="flex items-center gap-2.5 rounded-md border border-accent/40 bg-accent-subtle px-3 py-2">
          <FileText className="h-4 w-4 shrink-0 text-accent" aria-hidden />
          <span className="min-w-0 flex-1 truncate text-sm">
            {chosenSample.title}
            <span className="ml-2 text-xs text-muted-foreground">
              örnek doküman
            </span>
          </span>
          <button
            type="button"
            onClick={() => setSelectedSample(null)}
            aria-label="Örnek dokümanı kaldır"
            className="rounded p-1 text-muted-foreground hover:bg-surface hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" aria-hidden />
          </button>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={autoContinue}
            onChange={(event) => setAutoContinue(event.target.checked)}
            className="h-4 w-4 rounded border-input"
          />
          Model onayını atla, baştan sona çalıştır
        </label>

        <Button onClick={start} disabled={!canStart || starting} size="lg">
          {starting ? (
            <Loader2 className="animate-spin" aria-hidden />
          ) : (
            <Play aria-hidden />
          )}
          {starting ? "Başlatılıyor…" : "Analizi başlat"}
        </Button>
      </div>

      {readOnly ? (
        <p className="text-xs text-muted-foreground">
          Yönetici rolü salt okunurdur; analiz başlatmak için Güvenlik Uzmanı
          rolüne geçin.
        </p>
      ) : null}

      {/* Demo aid, kept out of the way. */}
      <div className="border-t border-border pt-3 text-center">
        {showSamples ? (
          <div className="space-y-2 text-left">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium">Örnek doküman seç</p>
              <button
                type="button"
                onClick={() => setShowSamples(false)}
                className="text-[11px] text-muted-foreground hover:text-foreground"
              >
                Kapat
              </button>
            </div>
            {samples === null ? (
              <p className="text-xs text-muted-foreground">Yükleniyor…</p>
            ) : (
              <ul className="grid gap-1.5 sm:grid-cols-3">
                {samples.map((sample) => (
                  <li key={sample.key}>
                    <button
                      type="button"
                      disabled={!sample.available}
                      onClick={() => {
                        setSelectedSample(sample.key);
                        setFiles([]);
                        setShowSamples(false);
                      }}
                      className={cn(
                        "w-full rounded-md border border-border p-2 text-left text-xs hover:border-accent/50 hover:bg-surface-muted disabled:opacity-40",
                        selectedSample === sample.key &&
                          "border-accent bg-accent-subtle",
                      )}
                    >
                      <span className="block truncate font-medium">
                        {sample.title}
                      </span>
                      <span className="block truncate text-[11px] text-muted-foreground">
                        {sample.focus}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-[11px] text-muted-foreground">
              Bu dokümanlar kurgusaldır; gerçek banka verisi içermezler.
            </p>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowSamples(true)}
            className="text-xs text-muted-foreground underline-offset-4 hover:text-accent hover:underline"
          >
            Elinizde doküman yok mu? Demo için örnek doküman kullanın
          </button>
        )}
      </div>

      {meta && !meta.llm_configured ? (
        <p className="rounded-md border border-level-high/40 bg-level-high/10 p-2.5 text-xs">
          LLM anahtarı tanımlı değil. Sistem modeli çıkarımı (2. adım) bu
          durumda hata verecek; Ayarlar ekranına bakın.
        </p>
      ) : null}

      {files.length > 0 || selectedSample ? (
        <p className="text-center text-[11px] text-muted-foreground">
          Dosyalar yalnızca bu bilgisayarda saklanır. Ücretsiz LLM
          katmanlarında gerçek müşteri verisi kullanmayın.
          {meta?.llm_model ? (
            <>
              {" "}
              Model: <Badge variant="default">{meta.llm_model}</Badge>
            </>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}
