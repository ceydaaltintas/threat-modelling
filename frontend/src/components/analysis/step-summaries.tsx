"use client";

import { Info } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LEVELS, levelClasses, levelForScore } from "@/lib/levels";
import { formatNumber } from "@/lib/format";
import type { MitigationOutput, RiskOutput, ValidationOutput } from "@/lib/types";
import { cn } from "@/lib/utils";

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border p-2.5">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}

/** Step 5: what validation checked and what it flagged. */
export function ValidationSummary({ output }: { output: ValidationOutput }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Doğrulama sonucu</CardTitle>
        <CardDescription>
          İşaretlenen tehditler listeden çıkarılmaz; ayrıntı tehdit
          çekmecesinde görünür ve kararı uzman verir.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-5">
        <Stat label="Kontrol edilen" value={formatNumber(output.checked)} />
        <Stat label="İşaretlenen" value={formatNumber(output.flagged)} />
        <Stat
          label="Bilinmeyen kaynak kimliği"
          value={formatNumber(output.unknown_ids)}
        />
        <Stat label="Tekrar" value={formatNumber(output.duplicates)} />
        <Stat
          label="Bulunamayan kanıt"
          value={formatNumber(output.evidence_missing)}
        />
      </CardContent>
    </Card>
  );
}

/** Step 6: level distribution and the 5x5 heat map of computed scores. */
export function RiskSummary({ output }: { output: RiskOutput }) {
  const scale = [1, 2, 3, 4, 5];
  const max = Math.max(1, ...Object.values(output.heatmap ?? {}));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Risk dağılımı</CardTitle>
        <CardDescription>
          Eşikler: ≤{output.thresholds.low} Düşük, ≤{output.thresholds.medium}{" "}
          Orta, ≤{output.thresholds.high} Yüksek, üzeri Kritik. Skorları kod
          hesaplar; LLM önerisi skora girmez.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid gap-3 sm:grid-cols-4">
          {LEVELS.map((level) => (
            <div
              key={level}
              className={cn("rounded-md border p-2.5", levelClasses[level])}
            >
              <p className="text-[11px]">{level}</p>
              <p className="mt-0.5 text-lg font-semibold tabular-nums">
                {formatNumber(output.by_level?.[level] ?? 0)}
              </p>
            </div>
          ))}
          {output.ai_level_differs > 0 ? (
            <p className="sm:col-span-4 flex items-start gap-1.5 text-[11px] text-muted-foreground">
              <Info className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
              {output.ai_level_differs} tehditte AI&apos;ın önerdiği seviye
              sistemin hesapladığından farklı. Her ikisi de çekmecede yan yana
              gösterilir.
            </p>
          ) : null}
        </div>

        <div>
          <div className="flex gap-1.5">
            {/* The same row height and gap as the grid. "self-start" is
                load bearing: as a stretched flex child this column grew to
                cover the x axis labels too, and its rows spread with it, so
                every label sat a little below its row. */}
            <div className="grid gap-1 self-start text-[10px] text-muted-foreground">
              {[...scale].reverse().map((value) => (
                <span
                  key={value}
                  className="flex h-8 items-center justify-end pr-0.5"
                >
                  {value}
                </span>
              ))}
            </div>
            <div className="flex-1">
              <div className="grid grid-cols-5 gap-1">
                {[...scale].reverse().map((impact) =>
                  scale.map((likelihood) => {
                    const count = output.heatmap?.[`${likelihood}x${impact}`] ?? 0;
                    const level = levelForScore(
                      impact * likelihood,
                      output.thresholds,
                    );
                    return (
                      <div
                        key={`${impact}-${likelihood}`}
                        title={`Olasılık ${likelihood} × Etki ${impact} = ${
                          impact * likelihood
                        } (${level}) · ${count} tehdit`}
                        className={cn(
                          "flex h-8 items-center justify-center rounded border text-[11px] font-medium",
                          levelClasses[level],
                          count === 0 && "opacity-35",
                        )}
                        style={count > 0 ? { opacity: 0.5 + (count / max) * 0.5 } : undefined}
                      >
                        {count || ""}
                      </div>
                    );
                  }),
                )}
              </div>
              <div className="mt-1 grid grid-cols-5 gap-1 text-center text-[10px] text-muted-foreground">
                {scale.map((value) => (
                  <span key={value}>{value}</span>
                ))}
              </div>
              <p className="mt-0.5 text-center text-[10px] text-muted-foreground">
                Yatay: olasılık · Dikey: etki
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/** Step 7: how many mitigations were proposed and mapped. */
export function MitigationSummary({ output }: { output: MitigationOutput }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Önlemler ve kontrol eşlemeleri</CardTitle>
        <CardDescription>
          Hangi önlemin uygulanacağını kural kataloğu belirler; LLM yalnızca
          önlemin bu sisteme nasıl uygulanacağını yazar.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-4">
          <Stat label="Önlem önerilen tehdit" value={formatNumber(output.threats)} />
          <Stat label="Kontrol eşlemesi" value={formatNumber(output.control_mappings)} />
          <Stat
            label="LLM ile yazılan metin"
            value={`${formatNumber(output.llm_written)}`}
          />
          <Stat
            label="LLM çağrısı"
            value={`${formatNumber(output.llm_calls)} / ${output.llm_budget}`}
          />
        </div>
        {output.llm_note ? (
          <p className="flex items-start gap-2 rounded-md border border-level-high/40 bg-level-high/10 p-2.5 text-xs">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-level-high" aria-hidden />
            {output.llm_note}
          </p>
        ) : null}
        <p className="text-[11px] text-muted-foreground">
          LLM bütçesi yalnızca Kritik ve Yüksek seviyeli tehditler için
          kullanılır; diğerleri katalog metnini alır.{" "}
          <Badge variant="warning">ISO maddeleri doğrulanacak</Badge>
        </p>
      </CardContent>
    </Card>
  );
}
