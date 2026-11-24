"use client";

import { BookOpen, Search } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { MATCH_LABELS, sourceLabel } from "@/lib/kb";
import type { RetrievalOutput } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Step 3 panel: which knowledge was retrieved for each component and flow. */
export function RetrievalPanel({ output }: { output: RetrievalOutput }) {
  const [selected, setSelected] = React.useState(0);
  const element = output.elements[selected];

  if (output.elements.length === 0) {
    return (
      <Card>
        <CardContent className="pt-5 text-sm text-muted-foreground">
          Bu adımda bilgi getirilmedi.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {output.degraded && output.note ? (
        <p className="rounded-md border border-level-high/40 bg-level-high/10 p-2.5 text-xs">
          {output.note}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
        <Card className="h-fit p-2">
          <ul className="space-y-0.5" aria-label="Model öğeleri">
            {output.elements.map((item, index) => (
              <li key={`${item.kind}-${item.id}`}>
                <button
                  type="button"
                  onClick={() => setSelected(index)}
                  aria-current={index === selected ? "true" : undefined}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-xs",
                    index === selected
                      ? "bg-accent-subtle text-accent"
                      : "hover:bg-surface-muted",
                  )}
                >
                  <span className="min-w-0 flex-1 truncate">{item.label}</span>
                  <Badge variant="outline">{item.sources.length}</Badge>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <BookOpen className="h-4 w-4 text-accent" aria-hidden />
              {element.label}
            </CardTitle>
            <CardDescription className="flex items-start gap-1.5">
              <Search className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
              <span className="break-words">
                Sorgu: <span className="italic">{element.query}</span>
              </span>
            </CardDescription>
          </CardHeader>
          <CardContent>
            {element.sources.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Bu öğe için kaynak bulunamadı.
              </p>
            ) : (
              <ul className="space-y-2">
                {element.sources.map((hit) => (
                  <li key={hit.id} className="rounded-md border border-border p-2.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="accent">{hit.identifier}</Badge>
                      <span className="text-xs font-medium">{hit.title}</span>
                      <Badge variant="outline">{sourceLabel(hit.source)}</Badge>
                      {hit.verification ? (
                        <Badge variant="warning">Doğrulanacak</Badge>
                      ) : null}
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">
                      {hit.text}
                    </p>
                    <p className="mt-1 flex flex-wrap gap-1.5 text-[10px] text-muted-foreground">
                      <span>Skor {hit.score}</span>
                      {hit.matched_by.map((engine) => (
                        <span key={engine}>· {MATCH_LABELS[engine] ?? engine}</span>
                      ))}
                    </p>
                  </li>
                ))}
              </ul>
            )}

            {/* The same question asked of the document itself. Without
                this the screen showed what the platform knows but not
                what it read. */}
            {element.passages && element.passages.length > 0 ? (
              <div className="mt-4 border-t border-border pt-3">
                <p className="mb-2 text-xs font-medium">
                  Dokümandan getirilen bölümler
                </p>
                <ul className="space-y-2">
                  {element.passages.map((passage, index) => (
                    <li
                      key={index}
                      className="rounded-md border border-border bg-surface-muted/40 p-2.5"
                    >
                      <p className="flex flex-wrap gap-1.5 text-[10px] text-muted-foreground">
                        {passage.page ? <span>Sayfa {passage.page}</span> : null}
                        {passage.section ? <span>· {passage.section}</span> : null}
                        <span>· Skor {passage.score}</span>
                        {passage.matched_by.map((engine) => (
                          <span key={engine}>
                            · {MATCH_LABELS[engine] ?? engine}
                          </span>
                        ))}
                      </p>
                      <p className="mt-1 line-clamp-3 text-[11px] leading-relaxed">
                        {passage.text}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <p className="text-xs text-muted-foreground">
        Bu adımda toplam{" "}
        <strong>{output.unique_identifiers.length}</strong> farklı kaynak
        kimliği getirildi. Tehdit üretiminde LLM'e yalnızca bu kimlikler
        verilir; başka bir kimlik yazarsa doğrulama adımında reddedilir.
      </p>
    </div>
  );
}
