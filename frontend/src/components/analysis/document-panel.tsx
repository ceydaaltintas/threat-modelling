"use client";

import { ChevronLeft, ChevronRight, FileText, Info } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatBytes, formatNumber } from "@/lib/format";
import type { DocumentOut } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Step 1 panel: extracted text with a page navigator and the section index. */
export function DocumentPanel({ documents }: { documents: DocumentOut[] }) {
  const [activeIndex, setActiveIndex] = React.useState(0);
  const [page, setPage] = React.useState(1);

  const document = documents[activeIndex];
  const pages = React.useMemo(
    () => (document?.section_map ?? []).filter((entry) => entry.type === "page"),
    [document],
  );
  const sections = React.useMemo(
    () => (document?.section_map ?? []).filter((entry) => entry.type === "section"),
    [document],
  );

  React.useEffect(() => setPage(1), [activeIndex]);

  if (!document) {
    return (
      <Card>
        <CardContent className="pt-5 text-sm text-muted-foreground">
          Bu analize ait doküman bulunamadı.
        </CardContent>
      </Card>
    );
  }

  const current = pages.find((entry) => entry.page === page) ?? pages[0];
  const text = document.raw_text ?? "";
  const pageText = current
    ? text.slice(current.start, current.end)
    : text.slice(0, 4000);
  const pageCount = pages.length || 1;

  return (
    <div className="space-y-4">
      {documents.length > 1 ? (
        <div className="flex flex-wrap gap-2">
          {documents.map((item, index) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveIndex(index)}
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs",
                index === activeIndex
                  ? "border-accent bg-accent-subtle text-accent"
                  : "border-border hover:bg-surface-muted",
              )}
            >
              {item.filename}
            </button>
          ))}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-accent" aria-hidden />
                  {document.filename}
                </CardTitle>
                <CardDescription>
                  {formatNumber(document.page_count)} sayfa ·{" "}
                  {formatNumber(text.length)} karakter ·{" "}
                  {formatBytes(document.size_bytes)} ·{" "}
                  {document.doc_type.toUpperCase()}
                </CardDescription>
              </div>
              {pageCount > 1 ? (
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="icon"
                    aria-label="Önceki sayfa"
                    disabled={page <= 1}
                    onClick={() => setPage((value) => Math.max(1, value - 1))}
                  >
                    <ChevronLeft aria-hidden />
                  </Button>
                  <span className="min-w-[72px] text-center text-xs text-muted-foreground">
                    Sayfa {page} / {pageCount}
                  </span>
                  <Button
                    variant="outline"
                    size="icon"
                    aria-label="Sonraki sayfa"
                    disabled={page >= pageCount}
                    onClick={() =>
                      setPage((value) => Math.min(pageCount, value + 1))
                    }
                  >
                    <ChevronRight aria-hidden />
                  </Button>
                </div>
              ) : null}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {document.extraction_note ? (
              <p className="flex items-start gap-2 rounded-md border border-border bg-surface-muted p-2.5 text-xs text-muted-foreground">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                {document.extraction_note}
              </p>
            ) : null}
            <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-md border border-border bg-surface-muted/40 p-3 font-sans text-xs leading-relaxed">
              {pageText.trim() || "Bu sayfada metin katmanı bulunamadı."}
            </pre>
          </CardContent>
        </Card>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-sm">Tespit edilen bölümler</CardTitle>
            <CardDescription>
              {sections.length > 0
                ? `${sections.length} başlık bulundu. Kanıt alıntıları bu bölümlere referans verir.`
                : "Numaralı başlık bulunamadı."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {sections.map((section) => (
                <li key={`${section.number}-${section.start}`}>
                  <button
                    type="button"
                    onClick={() => setPage(section.page)}
                    className="flex w-full items-start gap-2 rounded px-1.5 py-1 text-left text-xs hover:bg-surface-muted"
                  >
                    <Badge variant="outline" className="shrink-0">
                      {section.number}
                    </Badge>
                    <span className="min-w-0 flex-1 truncate">{section.title}</span>
                    <span className="shrink-0 text-[10px] text-muted-foreground">
                      s.{section.page}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
