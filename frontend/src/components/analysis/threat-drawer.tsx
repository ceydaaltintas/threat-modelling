"use client";

import {
  AlertCircle,
  Ban,
  Check,
  ExternalLink,
  Info,
  Pencil,
  ShieldCheck,
  X,
} from "lucide-react";
import * as React from "react";

import { EvidenceView } from "@/components/analysis/evidence-view";
import { RiskBreakdown } from "@/components/analysis/risk-breakdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";
import { levelClasses, type Level } from "@/lib/levels";
import { REVIEW_LABELS, STRIDE_LABELS, SOURCE_LABELS } from "@/lib/threats";
import { cn } from "@/lib/utils";
import type { DocumentOut, ReviewAction, ThreatRow } from "@/lib/types";

/** Right-hand drawer with everything known about one threat. */
export function ThreatDrawer({
  threat,
  documents,
  componentName,
  onClose,
  review,
  step,
}: {
  threat: ThreatRow | null;
  documents: DocumentOut[];
  componentName: (id: string | null) => string;
  onClose: () => void;
  /** The step this drawer was opened from; omit to show everything. */
  step?: number;
  review?: {
    readOnly: boolean;
    busy: boolean;
    onDecide: (
      threatId: string,
      action: ReviewAction,
      extra?: { note?: string; likelihood?: number; impact?: number; reason?: string },
    ) => Promise<void>;
  };
}) {
  React.useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  if (!threat) return null;

  // A step shows what the pipeline knew when it ran. Risk at step 4 or a
  // mitigation at step 5 did not exist yet, and showing them makes it
  // impossible to see what the step itself produced. Each later step adds
  // its own section; step 9 reaches all of them.
  const upTo = (producedAtStep: number) =>
    step === undefined || step >= producedAtStep;

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
              {threat.system_calc && upTo(6) ? (
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

          {upTo(5) ? (
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
          ) : null}

          {upTo(6) ? (
          <Section title="Risk">
            <RiskBreakdown threat={threat} />
            <p className="mt-2 text-[11px] text-muted-foreground">
              <strong className="font-medium text-foreground">
                Uzman onayı:
              </strong>{" "}
              {threat.expert?.level
                ? `${threat.expert.score} · ${threat.expert.level}`
                : threat.review_status === "pending"
                  ? "bekliyor"
                  : REVIEW_LABELS[threat.review_status] ?? threat.review_status}
              {threat.expert?.at
                ? ` · ${threat.expert.by} · ${formatDateTime(threat.expert.at)}`
                : ""}
            </p>
          </Section>
          ) : null}

          {upTo(7) ? (
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

          ) : null}

          {review ? (
            <Section title="Uzman kararı">
              <ReviewControls threat={threat} review={review} />
            </Section>
          ) : null}

          {upTo(7) ? (
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
          ) : null}
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

function ReviewControls({
  threat,
  review,
}: {
  threat: ThreatRow;
  review: NonNullable<Parameters<typeof ThreatDrawer>[0]["review"]>;
}) {
  const [note, setNote] = React.useState("");
  const [editing, setEditing] = React.useState(false);
  const computed = threat.system_calc;
  const [likelihood, setLikelihood] = React.useState(
    threat.expert?.likelihood ?? computed?.likelihood ?? 3,
  );
  const [impact, setImpact] = React.useState(
    threat.expert?.impact ?? computed?.impact ?? 3,
  );
  const [reason, setReason] = React.useState(threat.expert?.reason ?? "");

  const decided = threat.review_status !== "pending";
  // Changing a recorded decision is allowed - the expert may be wrong - but
  // the change is what an auditor will ask about, so it needs a reason.
  const needsReason = decided && note.trim() === "";
  const disabled = review.readOnly || review.busy;
  const changed =
    likelihood !== (computed?.likelihood ?? 0) ||
    impact !== (computed?.impact ?? 0);

  return (
    <div className="space-y-3">
      {decided ? (
        <p className="rounded-md bg-surface-muted p-2.5 text-xs">
          <strong>
            {REVIEW_LABELS[threat.review_status] ?? threat.review_status}
          </strong>
          {threat.expert?.by ? ` · ${threat.expert.by}` : ""}
          {threat.expert?.at ? ` · ${formatDateTime(threat.expert.at)}` : ""}
          {threat.expert?.reason || threat.expert?.note
            ? ` — ${threat.expert.reason || threat.expert.note}`
            : ""}
        </p>
      ) : null}

      <textarea
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder={
          decided
            ? "Kararı değiştirme gerekçesi (zorunlu)"
            : "Karar notu (isteğe bağlı)"
        }
        aria-label={decided ? "Kararı değiştirme gerekçesi" : "Karar notu"}
        rows={2}
        className={cn(
          "w-full rounded-md border bg-surface p-2 text-xs",
          needsReason ? "border-level-high" : "border-input",
        )}
      />

      {/* The decision that is already recorded is shown as current, not
          offered again: re-accepting an accepted threat does nothing but
          add a confusing second audit entry. */}
      {needsReason ? (
        <p className="text-[11px] text-level-high">
          Bu bulguda karar zaten kayıtlı. Değiştirmek için önce gerekçe yazın;
          eski karar denetim izinde kalır.
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <DecisionButton
          action="accept"
          current={threat.review_status}
          disabled={disabled || needsReason}
          onClick={() => review.onDecide(threat.id, "accept", { note })}
          icon={<Check aria-hidden />}
        >
          Kabul et
        </DecisionButton>
        <DecisionButton
          action="reject"
          current={threat.review_status}
          disabled={disabled || needsReason}
          onClick={() => review.onDecide(threat.id, "reject", { note })}
        >
          Reddet
        </DecisionButton>
        <DecisionButton
          action="false_positive"
          current={threat.review_status}
          disabled={disabled || needsReason}
          onClick={() => review.onDecide(threat.id, "false_positive", { note })}
          icon={<Ban aria-hidden />}
        >
          Yanlış pozitif
        </DecisionButton>
        <Button
          size="sm"
          variant="ghost"
          disabled={disabled}
          onClick={() => setEditing((value) => !value)}
        >
          <Pencil aria-hidden /> Seviyeyi düzenle
        </Button>
        {decided ? (
          <Button
            size="sm"
            variant="ghost"
            disabled={disabled || needsReason}
            onClick={() => review.onDecide(threat.id, "reset", { note })}
          >
            Kararı geri al
          </Button>
        ) : null}
      </div>

      {editing ? (
        <div className="space-y-2 rounded-md border border-border p-3">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <label className="flex items-center gap-1.5">
              Olasılık
              <select
                value={likelihood}
                onChange={(event) => setLikelihood(Number(event.target.value))}
                className="h-7 rounded border border-input bg-surface px-1.5"
              >
                {[1, 2, 3, 4, 5].map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5">
              Etki
              <select
                value={impact}
                onChange={(event) => setImpact(Number(event.target.value))}
                className="h-7 rounded border border-input bg-surface px-1.5"
              >
                {[1, 2, 3, 4, 5].map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <span className="text-muted-foreground">
              Yeni skor: <strong>{likelihood * impact}</strong>
              {computed ? ` (sistem hesabı: ${computed.score})` : ""}
            </span>
          </div>
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Seviye değişikliği için gerekçe (zorunlu)"
            aria-label="Seviye değişikliği gerekçesi"
            rows={2}
            className="w-full rounded-md border border-input bg-surface p-2 text-xs"
          />
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              disabled={disabled || !reason.trim() || !changed}
              onClick={async () => {
                await review.onDecide(threat.id, "edit", {
                  likelihood,
                  impact,
                  reason,
                  note,
                });
                setEditing(false);
              }}
            >
              Kaydet
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
              Vazgeç
            </Button>
            {!reason.trim() ? (
              <span className="text-[11px] text-level-high">
                Gerekçe zorunludur.
              </span>
            ) : !changed ? (
              <span className="text-[11px] text-muted-foreground">
                Sistem hesabıyla aynı; bir değer değiştirin.
              </span>
            ) : null}
          </div>
        </div>
      ) : null}

      {review.readOnly ? (
        <p className="text-[11px] text-muted-foreground">
          Yönetici rolü salt okunurdur; karar vermek için Güvenlik Uzmanı
          rolüne geçin.
        </p>
      ) : null}
    </div>
  );
}


const DECISION_STATUS: Record<string, string> = {
  accept: "accepted",
  reject: "rejected",
  false_positive: "false_positive",
};

/** A decision button that shows itself as current instead of repeating. */
function DecisionButton({
  action,
  current,
  disabled,
  onClick,
  icon,
  children,
}: {
  action: "accept" | "reject" | "false_positive";
  current: string;
  disabled: boolean;
  onClick: () => void;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  const isCurrent = DECISION_STATUS[action] === current;
  return (
    <Button
      size="sm"
      variant={action === "accept" && !isCurrent ? "default" : "outline"}
      disabled={disabled || isCurrent}
      aria-pressed={isCurrent}
      title={isCurrent ? "Bu karar zaten verildi" : undefined}
      onClick={onClick}
      className={cn(
        isCurrent &&
          "border-level-low/50 bg-level-low/10 text-level-low opacity-100",
      )}
    >
      {isCurrent ? <Check aria-hidden /> : icon}
      {children}
    </Button>
  );
}
