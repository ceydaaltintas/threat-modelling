"use client";

import { Badge } from "@/components/ui/badge";
import { levelClasses, type Level } from "@/lib/levels";
import type { ThreatRow } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * How the score was reached. One line per factor, each adjustment printed
 * with its reason, so the number can be argued with.
 *
 * The score used to be stated three times - headline, prose summary and a
 * "system calculation" box - which read as complexity rather than rigour.
 * It is said once; everything else explains how it got there.
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

  const ai = threat.ai_proposed;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline gap-2">
        <Badge className={cn("border", levelClasses[calc.level as Level])}>
          {calc.level}
        </Badge>
        <span className="text-sm font-semibold tabular-nums">{calc.score}</span>
        <span className="text-xs text-muted-foreground">
          = olasılık {calc.likelihood} × etki {calc.impact}
          <span className="text-muted-foreground/70"> (1–25)</span>
        </span>
      </div>

      <Row
        title="Olasılık"
        base={calc.base_likelihood}
        final={calc.likelihood}
        items={calc.breakdown.filter((item) => item.field === "likelihood")}
      />
      <Row
        title="Etki"
        base={calc.base_impact}
        final={calc.impact}
        items={calc.breakdown.filter((item) => item.field === "impact")}
      />

      {/* Only LLM-proposed threats carry a proposal; a rule threat has none,
          and an empty box said nothing. */}
      {ai?.likelihood && ai?.impact ? (
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          <strong className="font-medium text-foreground">AI önerisi:</strong>{" "}
          olasılık {ai.likelihood} × etki {ai.impact} — skora girmez, yalnızca
          karşılaştırma içindir.
          {ai.rationale ? ` ${ai.rationale}` : ""}
        </p>
      ) : null}
    </div>
  );
}

function Row({
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
    <div className="rounded-md border border-border px-2.5 py-2 text-xs">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="w-14 shrink-0 font-medium">{title}</span>
        <span className="tabular-nums text-muted-foreground">taban {base}</span>
        {items.map((item, index) => (
          <span
            key={index}
            className={cn(
              "tabular-nums",
              item.delta > 0 ? "text-level-critical" : "text-level-low",
            )}
          >
            {item.delta > 0 ? "+" : "−"}
            {Math.abs(item.delta)} {item.label}
          </span>
        ))}
        {items.length === 0 ? (
          <span className="text-muted-foreground">düzeltme yok</span>
        ) : null}
        <span className="ml-auto text-sm font-semibold tabular-nums">
          {final}
        </span>
      </div>
      {items.length > 0 ? (
        <ul className="mt-1 space-y-0.5 text-[11px] leading-relaxed text-muted-foreground sm:pl-16">
          {items.map((item, index) => (
            <li key={index}>{item.reason}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
