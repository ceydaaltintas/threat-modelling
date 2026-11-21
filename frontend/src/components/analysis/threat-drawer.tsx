"use client";

import { ExternalLink, X } from "lucide-react";
import * as React from "react";

import { EvidenceView } from "@/components/analysis/evidence-view";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { STRIDE_LABELS, SOURCE_LABELS } from "@/lib/threats";
import type { DocumentOut, ThreatRow } from "@/lib/types";

/** Right-hand drawer with everything known about one threat. */
export function ThreatDrawer({
  threat,
  documents,
  componentName,
  onClose,
}: {
  threat: ThreatRow | null;
  documents: DocumentOut[];
  componentName: (id: string | null) => string;
  onClose: () => void;
}) {
  React.useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  if (!threat) return null;

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div
        className="absolute inset-0 bg-black/20"
        onClick={onClose}
        aria-hidden
      />
      <aside
        role="dialog"
        aria-label="Tehdit ayrıntısı"
        className="relative flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-border bg-surface shadow-xl"
      >
        <header className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-border bg-surface px-5 py-4">
          <div className="min-w-0">
            <div className="mb-1 flex flex-wrap items-center gap-1.5">
              <Badge variant="outline">{STRIDE_LABELS[threat.stride]}</Badge>
              <Badge variant={threat.source === "rule" ? "default" : "accent"}>
                {SOURCE_LABELS[threat.source]}
              </Badge>
              {threat.rule_id ? (
                <Badge variant="outline">{threat.rule_id}</Badge>
              ) : null}
              {threat.is_assumption ? (
                <Badge variant="warning">Varsayım</Badge>
              ) : null}
            </div>
            <h2 className="text-sm font-semibold leading-snug">{threat.title}</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {componentName(threat.component_ref)}
              {threat.flow_ref ? ` · akış ${threat.flow_ref}` : ""}
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Kapat">
            <X aria-hidden />
          </Button>
        </header>

        <div className="space-y-5 px-5 py-4">
          <Section title="Açıklama">
            <p className="text-sm leading-relaxed">{threat.description || "—"}</p>
          </Section>

          <Section title="Saldırı senaryosu">
            <p className="text-sm leading-relaxed">{threat.scenario || "—"}</p>
          </Section>

          <Section title="Kanıt">
            <EvidenceView evidence={threat.evidence} documents={documents} />
          </Section>

          <Section title="Bilgi kaynakları">
            {threat.knowledge_sources.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Kaynak kimliği yok.
              </p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {threat.knowledge_sources.map((source) => (
                  <li key={source.id}>
                    <Badge variant="accent">
                      {source.id}
                      {source.url ? (
                        <a href={source.url} target="_blank" rel="noreferrer">
                          <ExternalLink className="h-3 w-3" aria-hidden />
                        </a>
                      ) : null}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Değerler">
            <div className="grid gap-3 sm:grid-cols-3">
              <ValueBox
                label="AI önerisi"
                value={
                  threat.ai_proposed?.likelihood && threat.ai_proposed?.impact
                    ? `O${threat.ai_proposed.likelihood} × E${threat.ai_proposed.impact}`
                    : "—"
                }
                note={threat.ai_proposed?.rationale ?? undefined}
              />
              <ValueBox
                label="Sistem hesabı"
                value={
                  threat.system_calc
                    ? `${threat.system_calc.score} · ${threat.system_calc.level}`
                    : "Aşama 3'te"
                }
                note={
                  threat.rule_context
                    ? `Taban: O${threat.rule_context.base_likelihood} × E${threat.rule_context.base_impact}`
                    : undefined
                }
              />
              <ValueBox
                label="Uzman onayı"
                value={threat.expert ? "Verildi" : "Aşama 4'te"}
              />
            </div>
            {threat.rule_context ? (
              <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                <li>
                  İnternete açık:{" "}
                  {threat.rule_context.internet_facing ? "Evet" : "Hayır"}
                </li>
                <li>
                  Hassas veri:{" "}
                  {threat.rule_context.sensitive_data ? "Evet" : "Hayır"}
                  {threat.rule_context.data_classes.length > 0
                    ? ` (${threat.rule_context.data_classes.join(", ")})`
                    : ""}
                </li>
                {threat.rule_context.control_evidence ? (
                  <li className="text-level-low">
                    Dokümanda önleme işaret eden ifade bulundu: “
                    {threat.rule_context.control_evidence}”
                  </li>
                ) : null}
              </ul>
            ) : null}
          </Section>

          <Section title="Önlemler">
            {threat.mitigations.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Önlem metinleri Aşama 3&apos;te üretilecek.
              </p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {threat.mitigations.map((item) => (
                  <li key={item.id}>
                    <Badge variant="outline">{item.id}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
      </aside>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-1.5">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      {children}
    </section>
  );
}

function ValueBox({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="rounded-md border border-border p-2.5">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-0.5 text-sm font-medium">{value}</p>
      {note ? (
        <p className="mt-0.5 text-[11px] text-muted-foreground">{note}</p>
      ) : null}
    </div>
  );
}
