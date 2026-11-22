"use client";

import {
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import {
  Ban,
  Check,
  ChevronRight,
  Filter,
  Info,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import * as React from "react";

import { ThreatDrawer } from "@/components/analysis/threat-drawer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  LEVELS,
  levelClasses,
  levelDot,
  levelText,
  type Level,
} from "@/lib/levels";
import { REVIEW_LABELS, SOURCE_LABELS, STRIDE_SHORT } from "@/lib/threats";
import type {
  DocumentOut,
  ReviewAction,
  ThreatListResponse,
  ThreatRow,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const STRIDE_ORDER = ["S", "T", "R", "I", "D", "E"];
const LEVEL_RANK: Record<string, number> = {
  Kritik: 0,
  Yüksek: 1,
  Orta: 2,
  Düşük: 3,
};

type SortKey = "level" | "component" | "stride";

const SORT_LABELS: Record<SortKey, string> = {
  level: "Seviyeye göre",
  component: "Bileşene göre",
  stride: "STRIDE'a göre",
};

export interface ReviewHandlers {
  readOnly: boolean;
  readOnlyReason?: string;
  busy: boolean;
  onDecide: (
    threatId: string,
    action: ReviewAction,
    extra?: {
      note?: string;
      likelihood?: number;
      impact?: number;
      reason?: string;
    },
  ) => Promise<void>;
  onBulk: (
    threatIds: string[],
    action: "accept" | "reject" | "false_positive" | "reset",
    note?: string,
  ) => Promise<void>;
}

/**
 * The threat list.
 *
 * Deliberately NOT a table: at the widths this product targets, a table with
 * level, score, title, component, STRIDE, source, evidence, validation and
 * review status pushes the most important column (the level) off screen and
 * forces horizontal scrolling. Each threat is one row that reflows instead.
 */
export function ThreatList({
  data,
  documents,
  componentNames,
  note,
  review,
  step,
}: {
  data: ThreatListResponse;
  documents: DocumentOut[];
  componentNames: Record<string, string>;
  note?: string | null;
  review?: ReviewHandlers;
  /** The step whose panel this list sits in; omit to show everything. */
  step?: number;
}) {
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: "level", desc: false },
  ]);
  const [search, setSearch] = React.useState("");
  const [stride, setStride] = React.useState("");
  const [level, setLevel] = React.useState("");
  const [source, setSource] = React.useState("");
  const [component, setComponent] = React.useState("");
  const [reviewFilter, setReviewFilter] = React.useState("");
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [checked, setChecked] = React.useState<Set<string>>(new Set());
  const [bulkNote, setBulkNote] = React.useState("");

  const selectedRows = React.useMemo(
    () => (data?.threats ?? []).filter((item) => checked.has(item.id)),
    [data, checked],
  );
  const bulkDecided = selectedRows.filter(
    (item) => item.review_status !== "pending",
  ).length;

  const nameOf = React.useCallback(
    (id: string | null) => (id ? componentNames[id] ?? id : "Sistem geneli"),
    [componentNames],
  );

  const filtered = React.useMemo(
    () =>
      data.threats.filter((threat) => {
        if (stride && threat.stride !== stride) return false;
        if (level && threat.system_calc?.level !== level) return false;
        if (source && threat.source !== source) return false;
        if (component && threat.component_ref !== component) return false;
        if (reviewFilter && threat.review_status !== reviewFilter) return false;
        if (search.trim()) {
          const needle = search.toLocaleLowerCase("tr");
          const haystack = [
            threat.title,
            threat.description ?? "",
            threat.scenario ?? "",
            threat.rule_id ?? "",
            nameOf(threat.component_ref),
            threat.knowledge_sources.map((s) => s.id).join(" "),
          ]
            .join(" ")
            .toLocaleLowerCase("tr");
          if (!haystack.includes(needle)) return false;
        }
        return true;
      }),
    [data.threats, stride, level, source, component, reviewFilter, search, nameOf],
  );

  // TanStack drives sorting; the rows are rendered by hand so they can reflow.
  const columns = React.useMemo<ColumnDef<ThreatRow>[]>(
    () => [
      {
        id: "level",
        accessorFn: (row) =>
          LEVEL_RANK[row.system_calc?.level ?? ""] * 100 -
          (row.system_calc?.score ?? 0),
      },
      { id: "component", accessorFn: (row) => nameOf(row.component_ref) },
      { id: "stride", accessorFn: (row) => STRIDE_ORDER.indexOf(row.stride) },
    ],
    [nameOf],
  );

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const rows = table.getRowModel().rows.map((row) => row.original);
  const components = React.useMemo(
    () =>
      Array.from(
        new Set(data.threats.map((t) => t.component_ref).filter(Boolean)),
      ) as string[],
    [data.threats],
  );

  const selected = selectedId
    ? data.threats.find((item) => item.id === selectedId) ?? null
    : null;
  const activeFilters =
    Boolean(search) || Boolean(stride) || Boolean(level) || Boolean(source) ||
    Boolean(component) || Boolean(reviewFilter);

  if (data.threats.length === 0) {
    return (
      <EmptyState
        icon={Filter}
        title="Tehdit üretilmedi"
        description="4. adım tamamlandığında kural kataloğunun ve LLM'in ürettiği tehditler burada listelenir."
      />
    );
  }

  const toggle = (id: string) =>
    setChecked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="space-y-3">
      {note ? (
        <p className="flex items-start gap-2 rounded-md border border-level-high/40 bg-level-high/10 p-2.5 text-xs">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-level-high" aria-hidden />
          {note}
        </p>
      ) : null}

      {/* Level counts first: this is what people scan for. */}
      <div className="flex flex-wrap items-center gap-2">
        {/* A level nothing fell into is not a filter: it cannot be clicked
            and says only that the level exists. */}
        {LEVELS.filter((value) => (data.summary.by_level?.[value] ?? 0) > 0).map(
          (value) => {
          const count = data.summary.by_level?.[value] ?? 0;
          const active = level === value;
          return (
            <button
              key={value}
              type="button"
              onClick={() => setLevel(active ? "" : value)}
              aria-pressed={active}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-colors disabled:opacity-40",
                "hover:bg-surface-muted",
                active ? "bg-surface-muted font-semibold" : "font-medium",
              )}
            >
              <span
                className={cn("h-1.5 w-1.5 rounded-full", levelDot[value])}
                aria-hidden
              />
              <span className={cn("tabular-nums", levelText[value])}>{count}</span>
              <span className={active ? levelText[value] : "text-foreground"}>
                {value}
              </span>
            </button>
          );
        },
        )}
        <span className="text-xs text-muted-foreground">
          · {data.summary.assumptions} varsayım
          {data.summary.flagged ? ` · ${data.summary.flagged} işaretli` : ""}
        </span>
      </div>

      {/* One row on a wide screen: every control shares the width and
          shrinks rather than pushing the last one off the card. Below that
          they wrap, because six controls cannot be read at 300px. */}
      <div className="flex flex-wrap items-center gap-1.5 lg:flex-nowrap">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Ara: tehdit, bileşen, kural, kaynak"
          aria-label="Tehditlerde ara"
          className="h-8 min-w-0 flex-[2] basis-full rounded-md border border-input bg-surface px-2.5 text-xs lg:basis-0"
        />
        <Select value={stride} onChange={setStride} label="STRIDE filtresi">
          <option value="">Tüm STRIDE</option>
          {STRIDE_ORDER.map((code) => (
            <option key={code} value={code}>
              {code} · {STRIDE_SHORT[code]}
            </option>
          ))}
        </Select>
        <Select value={component} onChange={setComponent} label="Bileşen filtresi">
          <option value="">Tüm bileşenler</option>
          {components.map((id) => (
            <option key={id} value={id}>
              {nameOf(id)}
            </option>
          ))}
        </Select>
        <Select value={source} onChange={setSource} label="Kaynak türü filtresi">
          <option value="">Tüm kaynaklar</option>
          {Object.entries(SOURCE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        {review ? (
          <Select value={reviewFilter} onChange={setReviewFilter} label="Karar filtresi">
            <option value="">Tüm kararlar</option>
            {Object.entries(REVIEW_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        ) : null}
        <Select
          value={(sorting[0]?.id as SortKey) ?? "level"}
          onChange={(value) => setSorting([{ id: value, desc: false }])}
          label="Sıralama"
        >
          {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => (
            <option key={key} value={key}>
              {SORT_LABELS[key]}
            </option>
          ))}
        </Select>
        {activeFilters ? (
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0"
            onClick={() => {
              setSearch("");
              setStride("");
              setLevel("");
              setSource("");
              setComponent("");
              setReviewFilter("");
            }}
          >
            Temizle
          </Button>
        ) : null}
      </div>

      <p className="text-xs text-muted-foreground">
        {rows.length === data.total
          ? `${data.total} tehdit`
          : `${rows.length} / ${data.total} tehdit`}{" "}
        · {data.summary.by_source.rule ?? 0} kuraldan,{" "}
        {data.summary.by_source.llm ?? 0} AI&apos;dan,{" "}
        {data.summary.by_source.merged ?? 0} birleştirilmiş
      </p>

      {review && !review.readOnly && checked.size > 0 ? (
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 rounded-md border border-accent/40 bg-accent-subtle px-3 py-2">
          <span className="text-xs font-medium">
            {checked.size} seçildi
            {bulkDecided > 0 ? (
              <span className="font-normal text-muted-foreground">
                {" "}
                · {bulkDecided} tanesinde karar var
              </span>
            ) : null}
          </span>
          <input
            value={bulkNote}
            onChange={(event) => setBulkNote(event.target.value)}
            placeholder={
              bulkDecided > 0
                ? "Kararı değiştirme gerekçesi (zorunlu)"
                : "Karar notu (isteğe bağlı)"
            }
            aria-label="Toplu karar notu"
            className={cn(
              "h-8 min-w-[200px] flex-1 rounded-md border bg-surface px-2.5 text-xs",
              bulkDecided > 0 && !bulkNote.trim()
                ? "border-level-high"
                : "border-input",
            )}
          />
          <BulkButton
            action="accept"
            rows={selectedRows}
            note={bulkNote}
            busy={review.readOnly || review.busy}
            onRun={async () => {
              await review.onBulk([...checked], "accept", bulkNote);
              setChecked(new Set());
              setBulkNote("");
            }}
            icon={<Check aria-hidden />}
          >
            Kabul et
          </BulkButton>
          <BulkButton
            action="false_positive"
            rows={selectedRows}
            note={bulkNote}
            busy={review.readOnly || review.busy}
            variant="outline"
            onRun={async () => {
              await review.onBulk([...checked], "false_positive", bulkNote);
              setChecked(new Set());
              setBulkNote("");
            }}
            icon={<Ban aria-hidden />}
          >
            Yanlış pozitif
          </BulkButton>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setChecked(new Set());
              setBulkNote("");
            }}
          >
            Seçimi bırak
          </Button>
        </div>
      ) : null}

      {review && !review.readOnly && rows.length > 0 ? (
        <button
          type="button"
          onClick={() => setChecked(new Set(rows.map((threat) => threat.id)))}
          className="text-xs text-accent hover:underline"
        >
          Görünen {rows.length} tehdidi seç
        </button>
      ) : null}

      <ul className="space-y-1.5">
        {rows.map((threat) => (
          <ThreatRowItem
            key={threat.id}
            threat={threat}
            componentName={nameOf(threat.component_ref)}
            onOpen={() => setSelectedId(threat.id)}
            selectable={Boolean(review) && !review?.readOnly}
            checked={checked.has(threat.id)}
            onToggle={() => toggle(threat.id)}
          />
        ))}
        {rows.length === 0 ? (
          <li className="rounded-md border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
            Bu filtrelerle eşleşen tehdit yok.
          </li>
        ) : null}
      </ul>

      <ThreatDrawer
        threat={selected}
        step={step}
        documents={documents}
        componentName={nameOf}
        onClose={() => setSelectedId(null)}
        review={review}
      />
    </div>
  );
}

function Select({
  value,
  onChange,
  label,
  children,
}: {
  value: string;
  onChange: (value: string) => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label={label}
      title={label}
      className="h-8 min-w-0 flex-1 basis-[140px] rounded-md border border-input bg-surface px-2 text-xs lg:basis-0"
    >
      {children}
    </select>
  );
}

/** One threat. Everything important is visible without scrolling sideways. */
function ThreatRowItem({
  threat,
  componentName,
  onOpen,
  selectable,
  checked,
  onToggle,
}: {
  threat: ThreatRow;
  componentName: string;
  onOpen: () => void;
  selectable: boolean;
  checked: boolean;
  onToggle: () => void;
}) {
  const calc = threat.system_calc;
  const expertLevel = threat.expert?.level;
  const level = (expertLevel ?? calc?.level) as Level | undefined;
  const score = threat.expert?.score ?? calc?.score;
  const errors = threat.validation_notes.filter(
    (note) => note.severity === "error",
  ).length;

  return (
    <li>
      <div
        className={cn(
          "group flex items-stretch gap-2 rounded-md border border-border bg-surface transition-colors hover:border-accent/50 hover:bg-surface-muted",
          checked && "border-accent/60 bg-accent-subtle",
        )}
      >
        {selectable ? (
          <label className="flex cursor-pointer items-center pl-2.5">
            <input
              type="checkbox"
              checked={checked}
              onChange={onToggle}
              aria-label={`${threat.title} seç`}
              className="h-3.5 w-3.5"
            />
          </label>
        ) : null}

        {/* Level is the first thing on the row, never off screen. */}
        <div
          className={cn(
            "flex w-[86px] shrink-0 flex-col items-center justify-center gap-0.5 rounded-l-md border-r px-1 py-2",
            level ? levelClasses[level] : "border-border text-muted-foreground",
            selectable && "rounded-l-none border-l",
          )}
        >
          <span className="text-sm font-semibold tabular-nums leading-none">
            {score ?? "—"}
          </span>
          <span className="text-[10px] font-medium leading-none">
            {level ?? "hesaplanmadı"}
          </span>
        </div>

        <button
          type="button"
          onClick={onOpen}
          className="flex min-w-0 flex-1 items-center gap-3 py-2 pr-2 text-left"
        >
          <span className="min-w-0 flex-1">
            <span className="block truncate text-xs font-medium">
              {threat.title}
            </span>
            <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
              <span className="truncate">{componentName}</span>
              <span aria-hidden>·</span>
              <span title={STRIDE_SHORT[threat.stride]}>
                {threat.stride} {STRIDE_SHORT[threat.stride]}
              </span>
              <span aria-hidden>·</span>
              <span>{SOURCE_LABELS[threat.source] ?? threat.source}</span>
              {threat.knowledge_sources.length > 0 ? (
                <>
                  <span aria-hidden>·</span>
                  <span className="truncate font-mono">
                    {threat.knowledge_sources
                      .slice(0, 3)
                      .map((item) => item.id)
                      .join(", ")}
                  </span>
                </>
              ) : null}
            </span>
          </span>

          <span className="flex shrink-0 items-center gap-1.5">
            {threat.is_assumption ? (
              <Badge variant="warning">Varsayım</Badge>
            ) : (
              <span
                className="flex items-center gap-0.5 text-[11px] text-level-low"
                title={`Dokümandan ${threat.evidence.length} kanıt alıntısı`}
              >
                <ShieldCheck className="h-3 w-3" aria-hidden />
                {threat.evidence.length} kanıt
              </span>
            )}
            {errors > 0 ? (
              <span
                className="flex items-center gap-0.5 text-[11px] text-level-critical"
                title="Doğrulamada işaretlendi"
              >
                <ShieldAlert className="h-3 w-3" aria-hidden />
                {errors}
              </span>
            ) : null}
            {threat.review_status !== "pending" ? (
              <Badge
                variant={
                  threat.review_status === "accepted" ||
                  threat.review_status === "edited"
                    ? "success"
                    : "default"
                }
              >
                {REVIEW_LABELS[threat.review_status]}
              </Badge>
            ) : null}
            <span className="ml-1 flex items-center gap-0.5 border-l border-border pl-2 text-[11px] text-muted-foreground group-hover:text-accent">
              Ayrıntı
              <ChevronRight className="h-3.5 w-3.5" aria-hidden />
            </span>
          </span>
        </button>
      </div>
    </li>
  );
}

/** What each bulk action leaves behind, so a button can tell whether it
 *  would change anything and whether that change needs a reason. */
const BULK_STATUS: Record<string, string> = {
  accept: "accepted",
  reject: "rejected",
  false_positive: "false_positive",
  reset: "pending",
};

function BulkButton({
  action,
  rows,
  note,
  busy,
  onRun,
  icon,
  variant,
  children,
}: {
  action: "accept" | "false_positive";
  rows: ThreatRow[];
  note: string;
  busy: boolean;
  onRun: () => Promise<void>;
  icon?: React.ReactNode;
  variant?: "outline";
  children: React.ReactNode;
}) {
  const target = BULK_STATUS[action];
  // Rows that already carry this decision would not change; rows that carry
  // a different one are an override, and an override needs a reason.
  const changes = rows.filter((item) => item.review_status !== target);
  const overrides = changes.filter((item) => item.review_status !== "pending");
  const blocked = overrides.length > 0 && note.trim() === "";
  const title =
    changes.length === 0
      ? "Seçilenlerin hepsinde bu karar zaten var"
      : blocked
        ? `${overrides.length} bulguda karar değişecek; önce gerekçe yazın`
        : `${changes.length} bulgu güncellenecek`;

  return (
    <Button
      size="sm"
      variant={variant}
      disabled={busy || changes.length === 0 || blocked}
      title={title}
      onClick={onRun}
    >
      {icon}
      {children}
      {changes.length > 0 && changes.length !== rows.length
        ? ` (${changes.length})`
        : ""}
    </Button>
  );
}
