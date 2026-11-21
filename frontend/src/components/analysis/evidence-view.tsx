"use client";

import { FileSearch, Quote, TriangleAlert } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import type { DocumentOut } from "@/lib/types";
import type { Evidence } from "@/lib/system-model";

const CONTEXT_CHARS = 260;

/** Casefold and collapse whitespace, mirroring the backend's check. */
function normalise(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase("tr").replace(/\s+/g, " ").trim();
}

interface Located {
  document: DocumentOut;
  before: string;
  match: string;
  after: string;
  page: number | null;
  section: string | null;
}

/**
 * Find the quote in the extracted text so it can be shown in context.
 * The backend already flagged quotes it could not find; this is the view.
 */
function locate(quote: string, documents: DocumentOut[]): Located | null {
  const needle = normalise(quote);
  if (needle.length < 8) return null;

  for (const document of documents) {
    const text = document.raw_text ?? "";
    if (!text) continue;

    // Walk the text building a normalised copy with an index map, so the
    // match can be mapped back to the original (accents, spacing intact).
    const map: number[] = [];
    let folded = "";
    let previousWasSpace = false;
    for (let index = 0; index < text.length; index += 1) {
      const char = text[index];
      const lowered = char.normalize("NFKC").toLocaleLowerCase("tr");
      if (/\s/.test(char)) {
        if (previousWasSpace || folded.length === 0) continue;
        folded += " ";
        map.push(index);
        previousWasSpace = true;
        continue;
      }
      previousWasSpace = false;
      folded += lowered;
      map.push(index);
    }

    const at = folded.indexOf(needle);
    if (at === -1) continue;

    const start = map[at] ?? 0;
    const endIndex = Math.min(at + needle.length - 1, map.length - 1);
    const end = (map[endIndex] ?? start) + 1;

    const page =
      (document.section_map ?? [])
        .filter((entry) => entry.type === "page")
        .find((entry) => start >= entry.start && start < entry.end)?.page ?? null;
    const section =
      (document.section_map ?? [])
        .filter((entry) => entry.type === "section")
        .filter((entry) => start >= entry.start && start < entry.end)
        .at(-1)?.label ?? null;

    return {
      document,
      before: text.slice(Math.max(0, start - CONTEXT_CHARS), start),
      match: text.slice(start, end),
      after: text.slice(end, end + CONTEXT_CHARS),
      page,
      section,
    };
  }
  return null;
}

export function EvidenceView({
  evidence,
  documents,
}: {
  evidence: Evidence[];
  documents: DocumentOut[];
}) {
  if (evidence.length === 0) {
    return (
      <div className="flex items-start gap-2 rounded-md border border-level-medium/40 bg-level-medium/10 p-3 text-xs">
        <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-level-medium" aria-hidden />
        <p>
          Bu öğe için dokümandan kanıt alıntısı yok; <strong>varsayım</strong>{" "}
          olarak değerlendirilmelidir.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {evidence.map((item, index) => {
        const located = locate(item.quote, documents);
        const notFound = (item.section ?? "").includes("dokümanda bulunamadı");
        return (
          <div
            key={`${item.quote}-${index}`}
            className="rounded-md border border-border bg-surface-muted/50 p-3"
          >
            <div className="mb-1.5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
              <Quote className="h-3 w-3" aria-hidden />
              {located?.page ?? item.page ? (
                <span>Sayfa {located?.page ?? item.page}</span>
              ) : null}
              {located?.section ? <span>· {located.section}</span> : null}
              {notFound || (!located && item.quote.length >= 12) ? (
                <Badge variant="warning">Alıntı dokümanda bulunamadı</Badge>
              ) : (
                <Badge variant="success">Dokümanda doğrulandı</Badge>
              )}
            </div>

            {located ? (
              <p className="text-xs leading-relaxed text-muted-foreground">
                …{located.before}
                <mark className="rounded bg-accent/20 px-0.5 text-foreground">
                  {located.match}
                </mark>
                {located.after}…
              </p>
            ) : (
              <p className="text-xs italic leading-relaxed">“{item.quote}”</p>
            )}
          </div>
        );
      })}
      <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <FileSearch className="h-3 w-3" aria-hidden />
        Vurgulanan bölüm, dokümandan çıkarılan metindeki yeridir.
      </p>
    </div>
  );
}
