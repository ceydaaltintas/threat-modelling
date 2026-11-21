"use client";

import {
  BookOpen,
  CircleCheck,
  FileText,
  Hammer,
  ListChecks,
  Network,
  RefreshCw,
  ShieldCheck,
  Sigma,
  UserCheck,
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
import { EmptyState } from "@/components/ui/empty-state";
import { formatDateTime } from "@/lib/format";
import type { Performer, RunStep, StepInfo } from "@/lib/types";

const PERFORMER_LABEL: Record<Performer, string> = {
  code: "Sistem hesabı",
  llm: "AI önerisi",
  "code+llm": "Kod + AI",
  human: "Uzman onayı",
};

const STEP_ICON: Record<number, LucideIcon> = {
  1: FileText,
  2: Network,
  3: BookOpen,
  4: Hammer,
  5: ShieldCheck,
  6: Sigma,
  7: ListChecks,
  8: UserCheck,
  9: CircleCheck,
};

/**
 * What each panel will contain once the matching phase is implemented.
 * Shown verbatim in phase 0 so nobody mistakes the shell for finished work.
 */
const PANEL_PLAN: Record<number, { phase: number; contents: string[] }> = {
  1: {
    phase: 1,
    contents: [
      "Doküman önizlemesi ve sayfa gezgini",
      "Çıkarılan metin uzunluğu ve tespit edilen bölümler",
    ],
  },
  2: {
    phase: 1,
    contents: [
      "DFD diyagramı (güven bölgeleri, bileşen ikonları, şifresiz akışlar kesikli)",
      "Düzenlenebilir bileşen ve akış tabloları",
      "“Dokümanda belirtilmemiş” ve “Varsayımlar” listeleri",
      "Öğeye tıklandığında kanıt alıntısı",
    ],
  },
  3: {
    phase: 2,
    contents: [
      "Bileşen başına getirilen bilgi kaynakları (kimlik, başlık, skor)",
    ],
  },
  4: {
    phase: 2,
    contents: [
      "Tehdit tablosu (seviye, STRIDE, kaynak türü, doğrulama durumu)",
      "Filtre çubuğu ve satır çekmecesi",
    ],
  },
  5: {
    phase: 3,
    contents: ["Doğrulama notları ve işaretlenen tehditler"],
  },
  6: {
    phase: 3,
    contents: [
      "Risk kırılımı (olasılık/etki düzeltmeleri sayısal olarak)",
      "AI önerisi / Sistem hesabı karşılaştırması",
    ],
  },
  7: {
    phase: 3,
    contents: ["Önlem metinleri ve kontrol eşlemeleri (ISO, NIST, ASVS)"],
  },
  8: {
    phase: 4,
    contents: [
      "Kabul / reddet / düzenle / yanlış pozitif ve toplu işlem çubuğu",
      "Seviye değişikliği için zorunlu gerekçe",
    ],
  },
  9: {
    phase: 4,
    contents: ["Rapor önizlemesi ve PDF / Excel / JSON indirme"],
  },
};

export function StepDetail({
  definition,
  step,
  paused,
  pauseReason,
  onResume,
  onRetry,
  busy,
  readOnly,
  buildPhase,
}: {
  definition: StepInfo | null;
  step: RunStep | null;
  paused: boolean;
  pauseReason: string | null;
  onResume: () => void;
  onRetry: () => void;
  busy: boolean;
  readOnly: boolean;
  buildPhase: number;
}) {
  if (!definition) {
    return (
      <EmptyState
        icon={ListChecks}
        title="Adım seçilmedi"
        description="Soldaki adım göstergesinden bir adıma tıklayın; o adımın çıktısı burada görünür."
      />
    );
  }

  const Icon = STEP_ICON[definition.no] ?? ListChecks;
  const plan = PANEL_PLAN[definition.no];
  const counters = Object.entries(step?.counters ?? {});

  const resumeLabel =
    pauseReason === "expert_review"
      ? "İncelemeyi tamamla ve devam et"
      : "Onayla ve devam et";

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-md bg-accent-subtle text-accent">
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <div>
                <CardTitle>
                  {definition.no}. {definition.name}
                </CardTitle>
                <CardDescription className="mt-1 max-w-2xl">
                  {definition.description}
                </CardDescription>
              </div>
            </div>
            <Badge variant="outline">{PERFORMER_LABEL[definition.performer]}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <dl className="grid gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs text-muted-foreground">Başlangıç</dt>
              <dd>{formatDateTime(step?.started_at)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Bitiş</dt>
              <dd>{formatDateTime(step?.finished_at)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Son mesaj</dt>
              <dd className="hyphenate">{step?.message ?? "—"}</dd>
            </div>
          </dl>

          {counters.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {counters.map(([key, value]) => (
                <Badge key={key} variant="accent">
                  {value} {definition.counter_labels[key] ?? key}
                </Badge>
              ))}
            </div>
          ) : null}

          {step?.status === "failed" ? (
            <div className="space-y-2 rounded-md border border-level-critical/40 bg-level-critical/10 p-3 text-sm">
              <p className="font-medium text-level-critical">
                Bu adım hata ile durdu.
              </p>
              <p className="text-muted-foreground">
                {step.message ?? "Ayrıntı için olay günlüğüne bakın."}
              </p>
              <Button variant="outline" size="sm" onClick={onRetry} disabled={readOnly}>
                <RefreshCw aria-hidden /> Bu adımı yeniden dene
              </Button>
            </div>
          ) : null}

          {paused ? (
            <div className="space-y-2 rounded-md border border-level-high/40 bg-level-high/10 p-3 text-sm">
              <p className="font-medium">Bu adım sizi bekliyor.</p>
              <p className="text-muted-foreground">
                {pauseReason === "expert_review"
                  ? "Tehditleri inceleyip kararınızı verdikten sonra analize devam edin."
                  : "Sistem modelini inceleyin, gerekiyorsa düzenleyin ve devam edin."}
              </p>
              <Button onClick={onResume} disabled={busy || readOnly}>
                {resumeLabel}
              </Button>
              {readOnly ? (
                <p className="text-xs text-muted-foreground">
                  Yönetici rolü salt okunurdur; devam etmek için Güvenlik Uzmanı
                  rolüne geçin.
                </p>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {plan && buildPhase < plan.phase ? (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="text-sm">
              Bu panel Aşama {plan.phase}&apos;de dolacak
            </CardTitle>
            <CardDescription>
              Aşama 0 iskelet aşamasıdır: adım akışı ve olay günlüğü gerçek, adım
              çıktıları henüz örnek veridir.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5 text-sm text-muted-foreground">
              {plan.contents.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
