"use client";

import { ScrollText } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AuditEntry } from "@/lib/types";

const ACTION_LABEL: Record<string, string> = {
  run_created: "Analiz oluşturuldu",
  run_resumed: "Analize devam edildi",
  run_cancelled: "Analiz iptal edildi",
  step_retried: "Adım yeniden çalıştırıldı",
  system_model_edited: "Sistem modeli düzenlendi",
  threat_accept: "Tehdit kabul edildi",
  threat_reject: "Tehdit reddedildi",
  threat_false_positive: "Yanlış pozitif işaretlendi",
  threat_edit: "Tehdit seviyesi değiştirildi",
  threat_reset: "Karar geri alındı",
};

const ROLE_LABEL: Record<string, string> = {
  security_expert: "Güvenlik Uzmanı",
  manager: "Yönetici",
  system: "Sistem",
};

/** Each entry is one line: who, when, what, and why if a reason was given. */
export default function AuditPage() {
  const [entries, setEntries] = React.useState<AuditEntry[] | null>(null);
  const [filter, setFilter] = React.useState("");

  React.useEffect(() => {
    api.audit().then(setEntries).catch(() => setEntries([]));
  }, []);

  const rows = (entries ?? []).filter((entry) => {
    if (!filter.trim()) return true;
    const needle = filter.toLocaleLowerCase("tr");
    return [
      entry.actor,
      entry.action,
      ACTION_LABEL[entry.action] ?? "",
      entry.reason ?? "",
      JSON.stringify(entry.new_value ?? {}),
    ]
      .join(" ")
      .toLocaleLowerCase("tr")
      .includes(needle);
  });

  return (
    <div className="mx-auto w-full max-w-4xl space-y-4 py-2">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Denetim izi</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Kim, ne zaman, neyi değiştirdi.
          </p>
        </div>
        <input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Kullanıcı, işlem veya gerekçe ara"
          aria-label="Denetim izinde ara"
          className="h-9 w-full max-w-xs rounded-md border border-input bg-surface px-3 text-sm"
        />
      </div>

      {entries === null ? (
        <SkeletonRows rows={6} />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          title={filter ? "Eşleşen kayıt yok" : "Denetim kaydı yok"}
          description={
            filter
              ? "Aramayı değiştirin."
              : "Analiz başlattığınızda ya da bir tehdit kararı verdiğinizde kayıtlar burada görünür."
          }
        />
      ) : (
        <>
          <p className="text-xs text-muted-foreground">
            {rows.length} kayıt · kayıtlar yalnızca eklenir, değiştirilmez
          </p>
          <ul className="space-y-1">
            {rows.map((entry) => (
              <li
                key={entry.id}
                className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 rounded-md border border-border bg-surface px-3 py-2 text-sm"
              >
                <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
                  {formatDateTime(entry.at)}
                </span>
                <span className="font-medium">
                  {ACTION_LABEL[entry.action] ?? entry.action}
                </span>
                <span className="text-xs text-muted-foreground">
                  {entry.actor}
                </span>
                <Badge variant="outline">
                  {ROLE_LABEL[entry.actor_role] ?? entry.actor_role}
                </Badge>
                {entry.reason ? (
                  <span className="w-full text-xs text-muted-foreground">
                    Gerekçe: {entry.reason}
                  </span>
                ) : null}
                {!entry.reason &&
                typeof entry.new_value?.title === "string" ? (
                  <span className="w-full truncate text-xs text-muted-foreground">
                    {entry.new_value.title as string}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
