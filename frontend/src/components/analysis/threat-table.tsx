"use client";

import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown, Ban, Check, Filter, Info } from "lucide-react";
import * as React from "react";

import { ThreatDrawer } from "@/components/analysis/threat-drawer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LEVELS, levelClasses, type Level } from "@/lib/levels";
import {
  REVIEW_LABELS,
  SOURCE_LABELS,
  STRIDE_SHORT,
  VALIDATION_LABELS,
} from "@/lib/threats";
import type {
  DocumentOut,
  ReviewAction,
  ThreatListResponse,
  ThreatRow,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const STRIDE_ORDER = ["S", "T", "R", "I", "D", "E"];

export function ThreatTable({
  data,
  documents,
  componentNames,
  note,
  review,
}: {
  data: ThreatListResponse;
  documents: DocumentOut[];
  componentNames: Record<string, string>;
  note?: string | null;
  /** Present in the expert review step: enables selection and decisions. */
  review?: {
    readOnly: boolean;
    busy: boolean;
    onDecide: (threatId: string, action: ReviewAction) => Promise<void>;
    onBulk: (
      threatIds: string[],
      action: "accept" | "reject" | "false_positive" | "reset",
    ) => Promise<void>;
  };
}) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [search, setSearch] = React.useState("");
  const [stride, setStride] = React.useState<string>("");
  const [source, setSource] = React.useState<string>("");
  const [component, setComponent] = React.useState<string>("");
  const [level, setLevel] = React.useState<string>("");
  const [reviewFilter, setReviewFilter] = React.useState<string>("");
  const [selected, setSelected] = React.useState<ThreatRow | null>(null);
  const [checked, setChecked] = React.useState<Set<string>>(new Set());

  const nameOf = React.useCallback(
    (id: string | null) => (id ? componentNames[id] ?? id : "Sistem geneli"),
    [componentNames],
  );

  const toggle = React.useCallback((id: string) => {
    setChecked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const columns = React.useMemo<ColumnDef<ThreatRow>[]>(
    () => [
      ...(review
        ? [
            {
              id: "select",
              header: "",
              cell: ({ row }: { row: { original: ThreatRow } }) => (
                <input
                  type="checkbox"
                  checked={checked.has(row.original.id)}
                  onChange={() => toggle(row.original.id)}
                  onClick={(event) => event.stopPropagation()}
                  aria-label={`${row.original.title} tehdidini seç`}
                  className="h-3.5 w-3.5"
                />
              ),
            } as ColumnDef<ThreatRow>,
          ]
        : []),
      {
        accessorKey: "title",
        header: "Tehdit",
        cell: ({ row }) => (
          <div className="min-w-0">
            <p className="truncate text-xs font-medium">{row.original.title}</p>
            <p className="truncate text-[11px] text-muted-foreground">
              {nameOf(row.original.component_ref)}
            </p>
          </div>
        ),
      },
      {
        accessorKey: "stride",
        header: "STRIDE",
        cell: ({ getValue }) => (
          <Badge variant="outline" title={STRIDE_SHORT[getValue<string>()]}>
            {getValue<string>()}
          </Badge>
        ),
        sortingFn: (a, b) =>
          STRIDE_ORDER.indexOf(a.original.stride) -
          STRIDE_ORDER.indexOf(b.original.stride),
      },
      {
        accessorKey: "source",
        header: "Kaynak",
        cell: ({ getValue }) => (
          <Badge variant={getValue<string>() === "rule" ? "default" : "accent"}>
            {SOURCE_LABELS[getValue<string>()] ?? getValue<string>()}
          </Badge>
        ),
      },
      {
        id: "evidence",
        header: "Kanıt",
        cell: ({ row }) =>
          row.original.is_assumption ? (
            <Badge variant="warning">Varsayım</Badge>
          ) : (
            <Badge variant="success">{row.original.evidence.length}</Badge>
          ),
      },
      {
        id: "sources",
        header: "Kaynak kimliği",
        cell: ({ row }) => (
          <span className="text-[11px] text-muted-foreground">
            {row.original.knowledge_sources.map((s) => s.id).join(", ") || "—"}
          </span>
        ),
      },
      ...(review
        ? [
            {
              id: "review",
              header: "Karar",
              cell: ({ row }: { row: { original: ThreatRow } }) => {
                const status = row.original.review_status;
                return status === "pending" ? (
                  <span className="text-[11px] text-muted-foreground">
                    Bekliyor
                  </span>
                ) : (
                  <Badge
                    variant={
                      status === "accepted" || status === "edited"
                        ? "success"
                        : "default"
                    }
                  >
                    {REVIEW_LABELS[status] ?? status}
                  </Badge>
                );
              },
            } as ColumnDef<ThreatRow>,
          ]
        : []),
      {
        accessorKey: "validation_status",
        header: "Doğrulama",
        cell: ({ row }) => {
          const status = row.original.validation_status;
          const errors = row.original.validation_notes.filter(
            (note) => note.severity === "error",
          ).length;
          if (status === "flagged") {
            return (
              <Badge variant={errors > 0 ? "danger" : "warning"}>
                İşaretli{errors > 0 ? ` (${errors})` : ""}
              </Badge>
            );
          }
          return (
            <span className="text-[11px] text-muted-foreground">
              {VALIDATION_LABELS[status] ?? status}
            </span>
          );
        },
      },
      {
        id: "level",
        header: "Seviye",
        accessorFn: (row) => row.system_calc?.score ?? -1,
        cell: ({ row }) =>
          row.original.system_calc ? (
            <span className="flex items-center gap-1.5">
              <Badge
                className={cn(
                  "border",
                  levelClasses[row.original.system_calc.level as Level],
                )}
              >
                {row.original.system_calc.level}
              </Badge>
              <span className="tabular-nums text-[11px] text-muted-foreground">
                {row.original.system_calc.score}
              </span>
            </span>
          ) : (
            <span className="text-[11px] text-muted-foreground">
              Hesaplanmadı
            </span>
          ),
      },
    ],
    [nameOf, review, checked, toggle],
  );

  const filtered = React.useMemo(
    () =>
      data.threats.filter((threat) => {
        if (stride && threat.stride !== stride) return false;
        if (level && threat.system_calc?.level !== level) return false;
        if (reviewFilter && threat.review_status !== reviewFilter) return false;
        if (source && threat.source !== source) return false;
        if (component && threat.component_ref !== component) return false;
        if (search.trim()) {
          const needle = search.toLocaleLowerCase("tr");
          const haystack = [
            threat.title,
            threat.description ?? "",
            threat.scenario ?? "",
            threat.rule_id ?? "",
            threat.knowledge_sources.map((s) => s.id).join(" "),
          ]
            .join(" ")
            .toLocaleLowerCase("tr");
          if (!haystack.includes(needle)) return false;
        }
        return true;
      }),
    [data.threats, stride, source, component, search],
  );

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const components = React.useMemo(
    () =>
      Array.from(
        new Set(data.threats.map((t) => t.component_ref).filter(Boolean)),
      ) as string[],
    [data.threats],
  );

  if (data.threats.length === 0) {
    return (
      <EmptyState
        icon={Filter}
        title="Tehdit üretilmedi"
        description="4. adım tamamlandığında kural kataloğunun ve LLM'in ürettiği tehditler burada listelenir."
      />
    );
  }

  return (
    <div className="space-y-3">
      {note ? (
        <p className="flex items-start gap-2 rounded-md border border-level-high/40 bg-level-high/10 p-2.5 text-xs">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-level-high" aria-hidden />
          {note}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Tehdit, kural veya kaynak ara"
          aria-label="Tehditlerde ara"
          className="h-8 min-w-[200px] flex-1 rounded-md border border-input bg-surface px-2.5 text-xs"
        />
        <select
          value={stride}
          onChange={(event) => setStride(event.target.value)}
          aria-label="STRIDE filtresi"
          className="h-8 rounded-md border border-input bg-surface px-2 text-xs"
        >
          <option value="">Tüm STRIDE</option>
          {STRIDE_ORDER.map((code) => (
            <option key={code} value={code}>
              {code} · {STRIDE_SHORT[code]}
            </option>
          ))}
        </select>
        <select
          value={level}
          onChange={(event) => setLevel(event.target.value)}
          aria-label="Seviye filtresi"
          className="h-8 rounded-md border border-input bg-surface px-2 text-xs"
        >
          <option value="">Tüm seviyeler</option>
          {LEVELS.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <select
          value={source}
          onChange={(event) => setSource(event.target.value)}
          aria-label="Kaynak türü filtresi"
          className="h-8 rounded-md border border-input bg-surface px-2 text-xs"
        >
          <option value="">Tüm kaynaklar</option>
          {Object.entries(SOURCE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={component}
          onChange={(event) => setComponent(event.target.value)}
          aria-label="Bileşen filtresi"
          className="h-8 max-w-[200px] rounded-md border border-input bg-surface px-2 text-xs"
        >
          <option value="">Tüm bileşenler</option>
          {components.map((id) => (
            <option key={id} value={id}>
              {nameOf(id)}
            </option>
          ))}
        </select>
        {review ? (
          <select
            value={reviewFilter}
            onChange={(event) => setReviewFilter(event.target.value)}
            aria-label="Karar durumu filtresi"
            className="h-8 rounded-md border border-input bg-surface px-2 text-xs"
          >
            <option value="">Tüm kararlar</option>
            {Object.entries(REVIEW_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        ) : null}
        {(search || stride || level || source || component || reviewFilter) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearch("");
              setStride("");
              setLevel("");
              setReviewFilter("");
              setSource("");
              setComponent("");
            }}
          >
            Filtreleri temizle
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>
          {filtered.length} / {data.total} tehdit ·{" "}
          {data.summary.by_source.rule ?? 0} kuraldan,{" "}
          {data.summary.by_source.llm ?? 0} LLM&apos;den,{" "}
          {data.summary.by_source.merged ?? 0} birleştirilmiş ·{" "}
          {data.summary.assumptions} varsayım
        </span>
        {data.summary.by_level
          ? LEVELS.filter((value) => data.summary.by_level?.[value]).map((value) => (
              <Badge key={value} className={cn("border", levelClasses[value])}>
                {data.summary.by_level?.[value]} {value}
              </Badge>
            ))
          : null}
        {data.summary.flagged ? (
          <Badge variant="warning">{data.summary.flagged} doğrulamada işaretli</Badge>
        ) : null}
      </div>

      {review && checked.size > 0 ? (
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-accent/40 bg-accent-subtle px-3 py-2">
          <span className="text-xs font-medium">
            {checked.size} tehdit seçildi
          </span>
          <Button
            size="sm"
            disabled={review.readOnly || review.busy}
            onClick={async () => {
              await review.onBulk([...checked], "accept");
              setChecked(new Set());
            }}
          >
            <Check aria-hidden /> Seçilenleri kabul et
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={review.readOnly || review.busy}
            onClick={async () => {
              await review.onBulk([...checked], "false_positive");
              setChecked(new Set());
            }}
          >
            <Ban aria-hidden /> Yanlış pozitif
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={review.readOnly || review.busy}
            onClick={async () => {
              await review.onBulk([...checked], "reset");
              setChecked(new Set());
            }}
          >
            Kararı geri al
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setChecked(new Set())}>
            Seçimi temizle
          </Button>
          {review.readOnly ? (
            <span className="text-[11px] text-muted-foreground">
              Yönetici rolü salt okunurdur.
            </span>
          ) : null}
        </div>
      ) : null}

      {review ? (
        <div className="flex items-center gap-2 text-xs">
          <button
            type="button"
            onClick={() =>
              setChecked(new Set(filtered.map((threat) => threat.id)))
            }
            className="text-accent hover:underline"
          >
            Görünen {filtered.length} tehdidi seç
          </button>
        </div>
      ) : null}

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="border-b border-border bg-surface-muted text-left text-[11px] text-muted-foreground">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="px-3 py-2 font-medium">
                      {header.isPlaceholder ? null : (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className={cn(
                            "flex items-center gap-1",
                            header.column.getCanSort() && "hover:text-foreground",
                          )}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          {header.column.getCanSort() ? (
                            <ArrowUpDown className="h-3 w-3 opacity-50" aria-hidden />
                          ) : null}
                        </button>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => setSelected(row.original)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-surface-muted"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2 align-top">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <ThreatDrawer
        threat={
          selected
            ? data.threats.find((item) => item.id === selected.id) ?? selected
            : null
        }
        documents={documents}
        componentName={nameOf}
        onClose={() => setSelected(null)}
        review={review}
      />
    </div>
  );
}
