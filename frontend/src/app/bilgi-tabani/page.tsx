"use client";

import { ExternalLink, Search } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { MATCH_LABELS, sourceLabel } from "@/lib/kb";
import type { KbSearchResult, KbStats } from "@/lib/types";

const EXAMPLES = ["CWE-89", "API1:2023", "loglara IBAN yazılıyor", "sertifika sabitleme"];

/** The knowledge base screen is a search tool; everything else is a footnote. */
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
      setResult(await api.kbSearch(value.trim(), 15));
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
    <div className="mx-auto w-full max-w-4xl space-y-4 py-2">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Bilgi tabanı</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Tehdit ve önlem üretiminde kullanılan kaynaklar.
        </p>
      </div>

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
          placeholder="Kimlik veya serbest metin ara"
          aria-label="Bilgi tabanında ara"
          className="h-10 min-w-0 flex-1 rounded-md border border-input bg-surface px-3 text-sm"
        />
        <Button type="submit" disabled={searching} size="lg">
          <Search aria-hidden /> {searching ? "Aranıyor…" : "Ara"}
        </Button>
      </form>

      <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
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
        <span className="ml-auto">
          {formatNumber(stats?.total_chunks)} kayıt · {sources.length} kaynak
          {stats?.vector_search ? " · hibrit arama" : " · anahtar kelime"}
        </span>
      </div>

      {error ? <p className="text-sm text-level-critical">{error}</p> : null}

      {result ? (
        <div className="space-y-2">
          {result.diagnostics.exact_identifiers.length > 0 ? (
            <p className="text-xs text-muted-foreground">
              Tam eşleşme: {result.diagnostics.exact_identifiers.join(", ")}
            </p>
          ) : null}
          {result.results.length === 0 ? (
            <p className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
              Sonuç bulunamadı.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {result.results.map((hit) => (
                <li
                  key={hit.id}
                  className="rounded-md border border-border bg-surface p-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="accent">{hit.identifier}</Badge>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">
                      {hit.title}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {sourceLabel(hit.source)}
                    </span>
                    {hit.verification ? (
                      <Badge variant="warning">Doğrulanacak</Badge>
                    ) : null}
                    {hit.url ? (
                      <a
                        href={hit.url}
                        target="_blank"
                        rel="noreferrer"
                        aria-label={`${hit.identifier} kaynağını aç`}
                        className="text-muted-foreground hover:text-accent"
                      >
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                      </a>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {hit.text}
                  </p>
                  <p className="mt-1 text-[10px] text-muted-foreground">
                    {hit.matched_by
                      .map((engine) => MATCH_LABELS[engine] ?? engine)
                      .join(" · ")}
                    {hit.license ? ` · ${hit.license}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className="rounded-md border border-border bg-surface">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-[11px] text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Kaynak</th>
                <th className="px-3 py-2 text-right font-medium">Kayıt</th>
              </tr>
            </thead>
            <tbody>
              {sources.map(([source, count]) => (
                <tr key={source} className="border-b border-border/60 last:border-0">
                  <td className="px-3 py-1.5">
                    <span className="block">{sourceLabel(source)}</span>
                    <span className="block text-[10px] text-muted-foreground">
                      {stats?.licenses[source] ?? "—"}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[11px] text-muted-foreground">
        Telifli standartların tam metni saklanmaz; yalnızca madde kimliği ve bu
        projede yazılmış kısa özet tutulur.{" "}
        {stats?.verification_needed
          ? `${stats.verification_needed} madde "doğrulanacak" işaretli.`
          : ""}
      </p>
    </div>
  );
}
