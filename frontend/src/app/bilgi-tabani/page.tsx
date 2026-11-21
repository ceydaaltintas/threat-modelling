"use client";

import { BookOpen, Search } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
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
import { api } from "@/lib/api";
import type { KbStats } from "@/lib/types";

const PLANNED_SOURCES = [
  { name: "MITRE ATT&CK (Enterprise + Mobile)", licence: "Apache-2.0 · atıf zorunlu" },
  { name: "MITRE CWE / CAPEC", licence: "Serbest kullanım · atıf zorunlu" },
  { name: "OWASP Top 10 / API Top 10 / MASVS / LLM Top 10", licence: "CC BY-SA 4.0 · kendi özetimiz" },
  { name: "STRIDE ve LINDDUN tanımları", licence: "Kendi özetimiz" },
  { name: "ISO/IEC 27001:2022 Ek A", licence: "Telifli · yalnızca madde kimliği + özet" },
  { name: "NIST SP 800-53", licence: "Kamu malı (ABD)" },
  { name: "OWASP ASVS", licence: "CC BY-SA 4.0" },
  { name: "BDDK yönetmelikleri, KVKK", licence: "Yalnızca başlık + bağlantı künyesi" },
];

export default function KnowledgeBasePage() {
  const [stats, setStats] = React.useState<KbStats | null>(null);
  const [query, setQuery] = React.useState("");
  const [result, setResult] = React.useState<string | null>(null);
  const [searching, setSearching] = React.useState(false);

  React.useEffect(() => {
    api.kbStats().then(setStats).catch(() => setStats(null));
  }, []);

  const search = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const response = await api.kbSearch(query.trim());
      setResult(
        response.results.length === 0
          ? `“${response.query}” için kayıt bulunamadı. ${response.note}`
          : response.results
              .map((item) => `${item.identifier} — ${item.title}`)
              .join("\n"),
      );
    } catch (err) {
      setResult((err as Error).message);
    } finally {
      setSearching(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Bilgi tabanı"
        description="Tehdit ve önlem üretiminde kullanılan kaynaklar. Her bilgi kimliğiyle ve atfıyla gösterilir."
      />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
        <Card>
          <CardHeader>
            <CardTitle>Kaynaklar</CardTitle>
            <CardDescription>
              Telifli standartların tam metni bilgi tabanına konmaz; yalnızca
              madde kimliği ve projede yazılmış kısa özet saklanır.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead className="border-b border-border text-left text-xs text-muted-foreground">
                <tr>
                  <th className="pb-2 font-medium">Kaynak</th>
                  <th className="pb-2 font-medium">Lisans / atıf</th>
                  <th className="pb-2 text-right font-medium">Kayıt</th>
                </tr>
              </thead>
              <tbody>
                {PLANNED_SOURCES.map((source) => (
                  <tr key={source.name} className="border-b border-border/60 last:border-0">
                    <td className="py-2 pr-3">{source.name}</td>
                    <td className="py-2 pr-3 text-xs text-muted-foreground">
                      {source.licence}
                    </td>
                    <td className="py-2 text-right tabular-nums text-muted-foreground">
                      {stats?.by_source && Object.keys(stats.by_source).length > 0
                        ? "—"
                        : 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-muted-foreground">
              Toplam kayıt: {stats?.total_chunks ?? 0}. Bilgi tabanı Aşama
              2&apos;de <code>backend/data/kb/*.jsonl</code> dosyalarından
              yüklenecek.
            </p>
          </CardContent>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Arama</CardTitle>
              <CardDescription>
                RAG&apos;i canlı test etmek için. Kimlik geçen sorgularda tam
                eşleşmeye öncelik verilir (örn. CWE-89).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <form onSubmit={search} className="flex gap-2">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="CWE-89"
                  aria-label="Bilgi tabanında ara"
                  className="h-9 min-w-0 flex-1 rounded-md border border-input bg-surface px-3 text-sm"
                />
                <Button type="submit" disabled={searching}>
                  <Search aria-hidden /> Ara
                </Button>
              </form>
              {result ? (
                <pre className="whitespace-pre-wrap rounded-md bg-surface-muted p-3 text-xs">
                  {result}
                </pre>
              ) : (
                <Badge variant="warning">Bilgi tabanı henüz boş (Aşama 2)</Badge>
              )}
            </CardContent>
          </Card>

          {!stats?.loaded ? (
            <EmptyState
              icon={BookOpen}
              title="Bilgi tabanı yüklenmedi"
              description="Ön işlenmiş JSONL dosyaları repoya dahil edilecek, böylece çalışma anında internet gerekmeyecek."
            />
          ) : null}
        </div>
      </div>
    </>
  );
}
