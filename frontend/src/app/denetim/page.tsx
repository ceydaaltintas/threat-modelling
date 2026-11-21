"use client";

import { ScrollText } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AuditEntry } from "@/lib/types";

const ACTION_LABEL: Record<string, string> = {
  run_created: "Analiz oluşturuldu",
  run_resumed: "Analize devam edildi",
  run_cancelled: "Analiz iptal edildi",
};

const ROLE_LABEL: Record<string, string> = {
  security_expert: "Güvenlik Uzmanı",
  manager: "Yönetici",
  system: "Sistem",
};

export default function AuditPage() {
  const [entries, setEntries] = React.useState<AuditEntry[] | null>(null);
  const [filter, setFilter] = React.useState("");

  React.useEffect(() => {
    api.audit().then(setEntries).catch(() => setEntries([]));
  }, []);

  const rows = (entries ?? []).filter((entry) => {
    if (!filter.trim()) return true;
    const needle = filter.toLocaleLowerCase("tr");
    return (
      entry.actor.toLocaleLowerCase("tr").includes(needle) ||
      entry.action.toLocaleLowerCase("tr").includes(needle) ||
      (ACTION_LABEL[entry.action] ?? "").toLocaleLowerCase("tr").includes(needle)
    );
  });

  return (
    <>
      <PageHeader
        title="Denetim izi"
        description="Kim, ne zaman, neyi değiştirdi. Kayıtlar eklenir; hiçbir zaman güncellenmez veya silinmez."
      />

      <input
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        placeholder="Kullanıcı veya işlem ara"
        aria-label="Denetim izinde ara"
        className="h-9 w-full max-w-sm rounded-md border border-input bg-surface px-3 text-sm"
      />

      {entries === null ? (
        <SkeletonRows rows={5} />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          title="Denetim kaydı yok"
          description="Bir analiz başlattığınızda ya da bir tehdit kararı verdiğinizde kayıtlar burada görünür."
        />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-surface-muted text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Zaman</th>
                  <th className="px-4 py-2.5 font-medium">Kullanıcı</th>
                  <th className="px-4 py-2.5 font-medium">Rol</th>
                  <th className="px-4 py-2.5 font-medium">İşlem</th>
                  <th className="px-4 py-2.5 font-medium">Nesne</th>
                  <th className="px-4 py-2.5 font-medium">Yeni değer</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((entry) => (
                  <tr key={entry.id} className="border-b border-border last:border-0">
                    <td className="whitespace-nowrap px-4 py-2.5 text-muted-foreground">
                      {formatDateTime(entry.at)}
                    </td>
                    <td className="px-4 py-2.5">{entry.actor}</td>
                    <td className="px-4 py-2.5">
                      <Badge variant="outline">
                        {ROLE_LABEL[entry.actor_role] ?? entry.actor_role}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5">
                      {ACTION_LABEL[entry.action] ?? entry.action}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                      {entry.object_type}
                      {entry.object_id ? ` · ${entry.object_id.slice(0, 8)}` : ""}
                    </td>
                    <td className="max-w-xs truncate px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                      {entry.new_value ? JSON.stringify(entry.new_value) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}
