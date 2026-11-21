"use client";

import { Calculator, Minus, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { levelClasses, type Level } from "@/lib/levels";
import type { ThreatRow } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * The numeric explanation behind a score. Every adjustment the code applied
 * is printed with its reason, so the number can be argued with.
 */
export function RiskBreakdown({ threat }: { threat: ThreatRow }) {
  const calc = threat.system_calc;
  if (!calc) {
    return (
      <p className="text-xs text-muted-foreground">
        Risk henüz hesaplanmadı (6. adım).
      </p>
    );
  }

  const likelihood = calc.breakdown.filter((item) => item.field === "likelihood");
  const impact = calc.breakdown.filter((item) => item.field === "impact");

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={cn("border", levelClasses[calc.level as Level])}>
          {calc.level}
        </Badge>
        <span className="text-sm font-medium tabular-nums">
          {calc.likelihood} × {calc.impact} = {calc.score}
        </span>
        <span className="text-[11px] text-muted-foreground">
          (olasılık × etki, 1–25)
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Column
          title="Olasılık"
          base={calc.base_likelihood}
          final={calc.likelihood}
          items={likelihood}
        />
        <Column
          title="Etki"
          base={calc.base_impact}
          final={calc.impact}
          items={impact}
        />
      </div>

      <p className="flex items-start gap-1.5 rounded-md bg-surface-muted p-2.5 text-[11px] leading-relaxed text-muted-foreground">
        <Calculator className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
        {calc.explanation}
      </p>

      {threat.ai_proposed?.likelihood && threat.ai_proposed?.impact ? (
        <p className="text-[11px] text-muted-foreground">
          AI önerisi: olasılık {threat.ai_proposed.likelihood}, etki{" "}
          {threat.ai_proposed.impact}. <strong>Bu öneri skora girmez</strong>;
          yalnızca karşılaştırma için gösterilir.
        </p>
      ) : null}
    </div>
  );
}

function Column({
  title,
  base,
  final,
  items,
}: {
  title: string;
  base: number;
  final: number;
  items: Array<{ label: string; delta: number; reason: string }>;
}) {
  return (
    <div className="rounded-md border border-border p-2.5">
      <div className="flex items-baseline justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          {title}
        </span>
        <span className="text-sm font-semibold tabular-nums">{final}</span>
      </div>
      <ul className="mt-1.5 space-y-1 text-[11px]">
        <li className="flex items-start gap-1.5 text-muted-foreground">
          <span className="w-8 shrink-0 tabular-nums">{base}</span>
          <span>taban değer</span>
        </li>
        {items.map((item, index) => (
          <li key={index} className="flex items-start gap-1.5">
            <span
              className={cn(
                "flex w-8 shrink-0 items-center gap-0.5 tabular-nums",
                item.delta > 0 ? "text-level-critical" : "text-level-low",
              )}
            >
              {item.delta > 0 ? (
                <Plus className="h-2.5 w-2.5" aria-hidden />
              ) : (
                <Minus className="h-2.5 w-2.5" aria-hidden />
              )}
              {Math.abs(item.delta)}
            </span>
            <span className="min-w-0">
              <span className="font-medium">{item.label}</span>
              <span className="block text-muted-foreground">{item.reason}</span>
            </span>
          </li>
        ))}
        {items.length === 0 ? (
          <li className="pl-[38px] text-muted-foreground">düzeltme yok</li>
        ) : null}
      </ul>
    </div>
  );
}
