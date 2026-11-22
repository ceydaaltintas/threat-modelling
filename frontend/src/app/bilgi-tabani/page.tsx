"use client";

import { BookOpen, Search, TriangleAlert } from "lucide-react";
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
import { SkeletonRows } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { MATCH_LABELS, sourceLabel } from "@/lib/kb";
import { formatNumber } from "@/lib/format";
import type { KbSearchResult, KbStats } from "@/lib/types";

const EXAMPLES = ["CWE-89", "API1:2023", "loglara IBAN yazılıyor", "sertifika sabitleme"];

export default function KnowledgeBasePage() {
  const [stats, setStats] = React.useState<KbStats | null>(null);
  const [query, setQuery] = React.useState("");
  const [result, setResult] = React.useState<KbSearchResult | null>(null);
  const [searching, setSearching] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api.kbStats().then(setStats).catch(() => setStats(null));
  }, []);

  const runSearch = React.useCallback(async (value: string) => {
    if (!value.trim()) return;
    setSearching(true);
    setError(null);
    try {
      setResult(await api.kbSearch(value.trim()));
    } catch (err) {
      setError((err as Error).message);
      setResult(null);
    } finally {
      setSearching(false);
    }
  }, []);

  const sources = Object.entries(stats?.by_source ?? {}).sort(
    ([, a], [, b]) => b - a,
  );

  return (
    <>
      <PageHeader
        title="Bilgi tabanı"
        description="Tehdit ve önlem üretiminde kullanılan kaynaklar."
      />

      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Toplam kayıt</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">
              {formatNumber(stats?.total_chunks)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Kaynak ailesi</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">
              {formatNumber(sources.length)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Doğrulanacak madde</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">
              {formatNumber(stats?.verification_needed)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Arama kipi</p>
            <p className="mt-1 text-sm font-medium">
              {stats?.vector_search ? (
                <Badge variant="success">Hibrit (kelime + vektör)</Badge>
              ) : (
                <Badge variant="warning">Yalnızca anahtar kelime</Badge>
              )}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-4 w-4 text-accent" aria-hidden />
            Arama
          </CardTitle>
          <CardDescription>
            Hibrit arama: anahtar kelime (Postgres full-text) ve anlamsal
            benzerlik (pgvector) sonuçları RRF ile birleştirilir. Sorguda bir
            kimlik geçiyorsa tam eşleşme en üste alınır.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void runSearch(query);
            }}
            className="flex gap-2"
          >
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="CWE-89 veya 'loglara IBAN yazılıyor'"
              aria-label="Bilgi tabanında ara"
              className="h-9 min-w-0 flex-1 rounded-md border border-input bg-surface px-3 text-sm"
            />
            <Button type="submit" disabled={searching}>
              <Search aria-hidden /> {searching ? "Aranıyor…" : "Ara"}
            </Button>
          </form>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            Örnekler:
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => {
                  setQuery(example);
                  void runSearch(example);
                }}
                className="rounded-full border border-border px-2 py-0.5 hover:bg-surface-muted"
              >
                {example}
              </button>
            ))}
          </div>

          {error ? <p className="text-sm text-level-critical">{error}</p> : null}

          {result ? (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <Badge variant={result.diagnostics.mode === "hybrid" ? "success" : "warning"}>
                  {result.diagnostics.mode === "hybrid"
                    ? "Hibrit arama"
                    : "Yalnızca anahtar kelime"}
                </Badge>
                {result.diagnostics.exact_identifiers.length > 0 ? (
                  <Badge variant="accent">
                    Tam eşleşme: {result.diagnostics.exact_identifiers.join(", ")}
                  </Badge>
                ) : null}
                <span>{result.results.length} sonuç</span>
                {result.diagnostics.note ? (
                  <span className="text-level-high">{result.diagnostics.note}</span>
                ) : null}
              </div>

              {result.results.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sonuç bulunamadı.</p>
              ) : (
                <ul className="space-y-2">
                  {result.results.map((hit) => (
                    <li
                      key={hit.id}
                      className="rounded-md border border-border p-3"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="accent">{hit.identifier}</Badge>
                        <span className="text-sm font-medium">{hit.title}</span>
                        <Badge variant="outline">{sourceLabel(hit.source)}</Badge>
                        {hit.verification ? (
                          <Badge variant="warning">Doğrulanacak</Badge>
                        ) : null}
                      </div>
                      <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                        {hit.text}
                      </p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                        <span>Skor {hit.score}</span>
                        {hit.matched_by.map((engine) => (
                          <Badge key={engine} variant="default">
                            {MATCH_LABELS[engine] ?? engine}
                          </Badge>
                        ))}
                        {hit.url ? (
                          <a
                            href={hit.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-accent hover:underline"
                          >
                            Kaynağa git
                          </a>
                        ) : null}
                      </div>
                      {hit.license ? (
                        <p className="mt-1 text-[10px] text-muted-foreground">
                          {hit.license}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Kaynaklar ve lisanslar</CardTitle>
          <CardDescription>
            Telifli standartların tam metni bilgi tabanına konmaz; yalnızca
            madde kimliği ve bu projede yazılmış kısa özet saklanır.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stats === null ? (
            <SkeletonRows rows={5} />
          ) : sources.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="Bilgi tabanı yüklenmedi"
              description="backend/data/kb/*.jsonl dosyaları bulunamadı. docker compose logs backend çıktısını kontrol edin."
            />
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-border text-left text-xs text-muted-foreground">
                <tr>
                  <th className="pb-2 font-medium">Kaynak</th>
                  <th className="pb-2 font-medium">Lisans / atıf</th>
                  <th className="pb-2 text-right font-medium">Kayıt</th>
                </tr>
              </thead>
              <tbody>
                {sources.map(([source, count]) => (
                  <tr key={source} className="border-b border-border/60 last:border-0">
                    <td className="py-2 pr-3 font-medium">{sourceLabel(source)}</td>
                    <td className="py-2 pr-3 text-xs text-muted-foreground">
                      {stats.licenses[source] ?? "—"}
                    </td>
                    <td className="py-2 text-right tabular-nums">{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {stats?.embedding_model ? (
            <p className="mt-3 flex items-start gap-1.5 text-[11px] text-muted-foreground">
              <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
              Gömme modeli: <code>{stats.embedding_model}</code> — yerel, CPU'da
              çalışır, API anahtarı gerektirmez.
            </p>
          ) : null}
        </CardContent>
      </Card>
    </>
  );
}
