"use client";

import { AlertCircle, ExternalLink, Info, ShieldCheck, X } from "lucide-react";
import * as React from "react";

import { EvidenceView } from "@/components/analysis/evidence-view";
import { RiskBreakdown } from "@/components/analysis/risk-breakdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { levelClasses, type Level } from "@/lib/levels";
import { STRIDE_LABELS, SOURCE_LABELS } from "@/lib/threats";
import { cn } from "@/lib/utils";
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
              {threat.system_calc ? (
                <Badge
                  className={cn(
                    "border",
                    levelClasses[threat.system_calc.level as Level],
                  )}
                >
                  {threat.system_calc.level} · {threat.system_calc.score}
                </Badge>
              ) : null}
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

          <Section title="Doğrulama">
            {threat.validation_notes.length === 0 ? (
              <p className="flex items-center gap-1.5 text-xs text-level-low">
                <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
                Tüm doğrulama kontrollerinden geçti.
              </p>
            ) : (
              <ul className="space-y-1.5">
                {threat.validation_notes.map((note, index) => (
                  <li
                    key={index}
                    className={cn(
                      "flex items-start gap-2 rounded-md border p-2 text-xs",
                      note.severity === "error"
                        ? "border-level-critical/40 bg-level-critical/10"
                        : note.severity === "warning"
                          ? "border-level-high/40 bg-level-high/10"
                          : "border-border bg-surface-muted",
                    )}
                  >
                    {note.severity === "info" ? (
                      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                    ) : (
                      <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                    )}
                    <span className="min-w-0">
                      <span className="font-medium">{note.label ?? note.code}</span>
                      {note.detail ? (
                        <span className="block break-words text-muted-foreground">
                          {note.detail}
                        </span>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-[11px] text-muted-foreground">
              İşaretlenen tehditler listeden çıkarılmaz; kararı uzman verir.
            </p>
          </Section>

          <Section title="Risk kırılımı (Sistem hesabı)">
            <RiskBreakdown threat={threat} />
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
                    : "Hesaplanmadı"
                }
                note={
                  threat.rule_context
                    ? `Taban: O${threat.rule_context.base_likelihood} × E${threat.rule_context.base_impact}`
                    : "STRIDE varsayılan tabanı"
                }
              />
              <ValueBox
                label="Uzman onayı"
                value={threat.expert ? "Verildi" : "Aşama 4'te"}
              />
            </div>
          </Section>

          <Section title="Önlemler">
            {threat.mitigations.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Önlem önerilmedi.
              </p>
            ) : (
              <ul className="space-y-2">
                {threat.mitigations.map((item) => (
                  <li key={item.id} className="rounded-md border border-border p-2.5">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-xs font-medium">
                        {item.title ?? item.id}
                      </span>
                      <Badge variant="outline">{item.id}</Badge>
                      {item.effort ? (
                        <Badge variant="default">Efor: {item.effort}</Badge>
                      ) : null}
                      <Badge variant={item.source === "llm" ? "accent" : "default"}>
                        {item.source === "llm" ? "AI metni" : "Katalog metni"}
                      </Badge>
                    </div>
                    {item.text ? (
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        {item.text}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Kontrol eşlemeleri">
            {threat.control_mappings.length === 0 ? (
              <p className="text-xs text-muted-foreground">Eşleme yok.</p>
            ) : (
              <>
                <table className="w-full text-xs">
                  <thead className="text-left text-[11px] text-muted-foreground">
                    <tr>
                      <th className="pb-1 font-medium">Çerçeve</th>
                      <th className="pb-1 font-medium">Madde</th>
                      <th className="pb-1 font-medium">Durum</th>
                      <th className="pb-1 font-medium">Önlem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {threat.control_mappings.map((item) => (
                      <tr
                        key={`${item.framework}-${item.id}`}
                        className="border-t border-border/60"
                      >
                        <td className="py-1 pr-2">{item.framework}</td>
                        <td className="py-1 pr-2 font-mono">{item.id}</td>
                        <td className="py-1 pr-2">
                          {item.verification === "needed" ? (
                            <Badge variant="warning">Doğrulanacak</Badge>
                          ) : (
                            <Badge variant="success">Teyitli</Badge>
                          )}
                        </td>
                        <td className="py-1 text-muted-foreground">{item.via}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-1.5 text-[11px] text-muted-foreground">
                  ISO maddeleri “doğrulanacak” işaretlidir: standardın metni
                  telifli olduğu için madde numarası kurumun kendi nüshasından
                  teyit edilmelidir.
                </p>
              </>
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
