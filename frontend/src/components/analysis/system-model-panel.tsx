"use client";

import {
  CircleHelp,
  GitBranch,
  Lightbulb,
  Network,
  Plus,
  Save,
  Table2,
  Trash2,
  Undo2,
} from "lucide-react";
import * as React from "react";

import { Dfd } from "@/components/analysis/dfd";
import { EvidenceView } from "@/components/analysis/evidence-view";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  COMPONENT_TYPE_LABELS,
  EMPTY_MODEL,
  SENSITIVITY_LABELS,
  maybeLabel,
  type ComponentType,
  type MaybeBool,
  type SmComponent,
  type SmFlow,
  type SystemModelData,
  type SystemModelVersion,
} from "@/lib/system-model";
import type { DocumentOut } from "@/lib/types";
import { cn } from "@/lib/utils";

type Tab = "diagram" | "components" | "flows" | "gaps";

const TABS: Array<{ key: Tab; label: string; icon: typeof Network }> = [
  { key: "diagram", label: "Diyagram", icon: Network },
  { key: "components", label: "Bileşenler", icon: Table2 },
  { key: "flows", label: "Veri akışları", icon: GitBranch },
  { key: "gaps", label: "Belirsizler ve varsayımlar", icon: CircleHelp },
];

const MAYBE_OPTIONS: MaybeBool[] = [true, false, "unknown"];

function cellInput(className?: string) {
  return cn(
    "h-7 w-full min-w-0 rounded border border-transparent bg-transparent px-1.5 text-xs",
    "hover:border-input focus:border-input focus:bg-surface",
    className,
  );
}

export function SystemModelPanel({
  version,
  documents,
  onSave,
  saving,
  readOnly,
  dirtyRef,
}: {
  version: SystemModelVersion | null;
  documents: DocumentOut[];
  onSave: (data: SystemModelData, reason: string) => Promise<void>;
  saving: boolean;
  readOnly: boolean;
  dirtyRef?: React.MutableRefObject<boolean>;
}) {
  const [tab, setTab] = React.useState<Tab>("diagram");
  const [draft, setDraft] = React.useState<SystemModelData>(
    version?.data ?? EMPTY_MODEL,
  );
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [dirty, setDirty] = React.useState(false);

  // A newly extracted version replaces the draft; an in-progress edit is kept.
  const versionId = version?.id ?? null;
  React.useEffect(() => {
    setDraft(version?.data ?? EMPTY_MODEL);
    setDirty(false);
  }, [versionId, version?.data]);

  React.useEffect(() => {
    if (dirtyRef) dirtyRef.current = dirty;
  }, [dirty, dirtyRef]);

  const update = React.useCallback((next: SystemModelData) => {
    setDraft(next);
    setDirty(true);
  }, []);

  const patchComponent = (id: string, patch: Partial<SmComponent>) =>
    update({
      ...draft,
      components: draft.components.map((item) =>
        item.id === id ? { ...item, ...patch } : item,
      ),
    });

  const patchFlow = (id: string, patch: Partial<SmFlow>) =>
    update({
      ...draft,
      data_flows: draft.data_flows.map((item) =>
        item.id === id ? { ...item, ...patch } : item,
      ),
    });

  const removeComponent = (id: string) =>
    update({
      ...draft,
      components: draft.components.filter((item) => item.id !== id),
      // Flows that lose an endpoint cannot stay in the model.
      data_flows: draft.data_flows.filter(
        (flow) => flow.source_id !== id && flow.target_id !== id,
      ),
    });

  const addComponent = () => {
    const id = `yeni-bilesen-${draft.components.length + 1}`;
    update({
      ...draft,
      components: [
        ...draft.components,
        {
          id,
          name: "Yeni bileşen",
          type: "other",
          technology: null,
          trust_zone: null,
          internet_facing: "unknown",
          authentication: null,
          description: null,
          evidence: [],
        },
      ],
    });
    setSelectedId(id);
    setTab("components");
  };

  const addFlow = () => {
    if (draft.components.length < 2) return;
    const id = `yeni-akis-${draft.data_flows.length + 1}`;
    update({
      ...draft,
      data_flows: [
        ...draft.data_flows,
        {
          id,
          source_id: draft.components[0].id,
          target_id: draft.components[1].id,
          protocol: null,
          encrypted: "unknown",
          authenticated: "unknown",
          data_classes: [],
          description: null,
          evidence: [],
        },
      ],
    });
    setSelectedId(id);
    setTab("flows");
  };

  const selectedComponent =
    draft.components.find((item) => item.id === selectedId) ?? null;
  const selectedFlow = draft.data_flows.find((item) => item.id === selectedId) ?? null;

  const save = async () => {
    await onSave(draft, "Uzman, çıkarılan sistem modelini düzenledi.");
    setDirty(false);
  };

  if (!version) {
    return (
      <Card>
        <CardContent className="pt-5 text-sm text-muted-foreground">
          Sistem modeli henüz çıkarılmadı. 2. adım tamamlandığında burada
          görünecek.
        </CardContent>
      </Card>
    );
  }

  const withoutEvidence = [
    ...draft.components.filter((item) => item.evidence.length === 0),
    ...draft.data_flows.filter((item) => item.evidence.length === 0),
  ].length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {TABS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setTab(item.key)}
              aria-pressed={tab === item.key}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
                tab === item.key
                  ? "bg-accent-subtle text-accent"
                  : "text-muted-foreground hover:bg-surface-muted",
              )}
            >
              <item.icon className="h-3.5 w-3.5" aria-hidden />
              {item.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Badge variant={version.source === "expert" ? "success" : "accent"}>
            {version.source === "expert" ? "Uzman onayı" : "AI önerisi"} · sürüm{" "}
            {version.version}
          </Badge>
          {withoutEvidence > 0 ? (
            <Badge variant="warning">{withoutEvidence} kanıtsız öğe</Badge>
          ) : null}
          {dirty ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setDraft(version.data);
                  setDirty(false);
                }}
              >
                <Undo2 aria-hidden /> Geri al
              </Button>
              <Button size="sm" onClick={save} disabled={saving || readOnly}>
                <Save aria-hidden />
                {saving ? "Kaydediliyor…" : "Değişiklikleri kaydet"}
              </Button>
            </>
          ) : null}
        </div>
      </div>

      {tab === "diagram" ? (
        <Dfd
          model={draft}
          selectedId={selectedId}
          onSelectComponent={setSelectedId}
          onSelectFlow={setSelectedId}
        />
      ) : null}

      {tab === "components" ? (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="border-b border-border bg-surface-muted text-left text-[11px] text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">Ad</th>
                  <th className="px-3 py-2 font-medium">Tür</th>
                  <th className="px-3 py-2 font-medium">Teknoloji</th>
                  <th className="px-3 py-2 font-medium">Güven bölgesi</th>
                  <th className="px-3 py-2 font-medium">İnternete açık</th>
                  <th className="px-3 py-2 font-medium">Kanıt</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {draft.components.map((component) => (
                  <tr
                    key={component.id}
                    onClick={() => setSelectedId(component.id)}
                    className={cn(
                      "cursor-pointer border-b border-border last:border-0",
                      selectedId === component.id
                        ? "bg-accent-subtle"
                        : "hover:bg-surface-muted",
                    )}
                  >
                    <td className="px-3 py-1.5">
                      <input
                        value={component.name}
                        readOnly={readOnly}
                        onChange={(event) =>
                          patchComponent(component.id, { name: event.target.value })
                        }
                        className={cellInput("font-medium")}
                        aria-label="Bileşen adı"
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={component.type}
                        disabled={readOnly}
                        onChange={(event) =>
                          patchComponent(component.id, {
                            type: event.target.value as ComponentType,
                          })
                        }
                        className={cellInput()}
                        aria-label="Bileşen türü"
                      >
                        {Object.entries(COMPONENT_TYPE_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        value={component.technology ?? ""}
                        readOnly={readOnly}
                        placeholder="Belirtilmemiş"
                        onChange={(event) =>
                          patchComponent(component.id, {
                            technology: event.target.value || null,
                          })
                        }
                        className={cellInput()}
                        aria-label="Teknoloji"
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        value={component.trust_zone ?? ""}
                        readOnly={readOnly}
                        placeholder="Belirtilmemiş"
                        onChange={(event) =>
                          patchComponent(component.id, {
                            trust_zone: event.target.value || null,
                          })
                        }
                        className={cellInput()}
                        aria-label="Güven bölgesi"
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={String(component.internet_facing)}
                        disabled={readOnly}
                        onChange={(event) =>
                          patchComponent(component.id, {
                            internet_facing: parseMaybe(event.target.value),
                          })
                        }
                        className={cellInput()}
                        aria-label="İnternete açık mı"
                      >
                        {MAYBE_OPTIONS.map((value) => (
                          <option key={String(value)} value={String(value)}>
                            {maybeLabel(value)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      {component.evidence.length > 0 ? (
                        <Badge variant="success">{component.evidence.length}</Badge>
                      ) : (
                        <Badge variant="warning">Varsayım</Badge>
                      )}
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      <button
                        type="button"
                        disabled={readOnly}
                        onClick={(event) => {
                          event.stopPropagation();
                          removeComponent(component.id);
                        }}
                        className="rounded p-1 text-muted-foreground hover:bg-surface hover:text-level-critical disabled:opacity-40"
                        aria-label={`${component.name} bileşenini kaldır`}
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <CardContent className="pt-3">
            <Button variant="outline" size="sm" onClick={addComponent} disabled={readOnly}>
              <Plus aria-hidden /> Bileşen ekle
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {tab === "flows" ? (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="border-b border-border bg-surface-muted text-left text-[11px] text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">Kaynak</th>
                  <th className="px-3 py-2 font-medium">Hedef</th>
                  <th className="px-3 py-2 font-medium">Protokol</th>
                  <th className="px-3 py-2 font-medium">Şifreli</th>
                  <th className="px-3 py-2 font-medium">Kimlik doğrulamalı</th>
                  <th className="px-3 py-2 font-medium">Veri sınıfları</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {draft.data_flows.map((flow) => (
                  <tr
                    key={flow.id}
                    onClick={() => setSelectedId(flow.id)}
                    className={cn(
                      "cursor-pointer border-b border-border last:border-0",
                      selectedId === flow.id
                        ? "bg-accent-subtle"
                        : "hover:bg-surface-muted",
                    )}
                  >
                    <td className="px-3 py-1.5">
                      <select
                        value={flow.source_id}
                        disabled={readOnly}
                        onChange={(event) =>
                          patchFlow(flow.id, { source_id: event.target.value })
                        }
                        className={cellInput()}
                        aria-label="Kaynak bileşen"
                      >
                        {draft.components.map((component) => (
                          <option key={component.id} value={component.id}>
                            {component.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={flow.target_id}
                        disabled={readOnly}
                        onChange={(event) =>
                          patchFlow(flow.id, { target_id: event.target.value })
                        }
                        className={cellInput()}
                        aria-label="Hedef bileşen"
                      >
                        {draft.components.map((component) => (
                          <option key={component.id} value={component.id}>
                            {component.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        value={flow.protocol ?? ""}
                        readOnly={readOnly}
                        placeholder="Belirtilmemiş"
                        onChange={(event) =>
                          patchFlow(flow.id, { protocol: event.target.value || null })
                        }
                        className={cellInput()}
                        aria-label="Protokol"
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={String(flow.encrypted)}
                        disabled={readOnly}
                        onChange={(event) =>
                          patchFlow(flow.id, { encrypted: parseMaybe(event.target.value) })
                        }
                        className={cn(
                          cellInput(),
                          flow.encrypted === false && "text-level-critical",
                        )}
                        aria-label="Şifreli mi"
                      >
                        {MAYBE_OPTIONS.map((value) => (
                          <option key={String(value)} value={String(value)}>
                            {maybeLabel(value)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={String(flow.authenticated)}
                        disabled={readOnly}
                        onChange={(event) =>
                          patchFlow(flow.id, {
                            authenticated: parseMaybe(event.target.value),
                          })
                        }
                        className={cn(
                          cellInput(),
                          flow.authenticated === false && "text-level-critical",
                        )}
                        aria-label="Kimlik doğrulamalı mı"
                      >
                        {MAYBE_OPTIONS.map((value) => (
                          <option key={String(value)} value={String(value)}>
                            {maybeLabel(value)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-1.5 text-muted-foreground">
                      {flow.data_classes.length > 0
                        ? flow.data_classes.join(", ")
                        : "—"}
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      <button
                        type="button"
                        disabled={readOnly}
                        onClick={(event) => {
                          event.stopPropagation();
                          update({
                            ...draft,
                            data_flows: draft.data_flows.filter(
                              (item) => item.id !== flow.id,
                            ),
                          });
                        }}
                        className="rounded p-1 text-muted-foreground hover:bg-surface hover:text-level-critical disabled:opacity-40"
                        aria-label="Akışı kaldır"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <CardContent className="pt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={addFlow}
              disabled={readOnly || draft.components.length < 2}
            >
              <Plus aria-hidden /> Akış ekle
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {tab === "gaps" ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <CircleHelp className="h-4 w-4 text-level-medium" aria-hidden />
                Dokümanda belirtilmemiş ({draft.unknowns.length})
              </CardTitle>
              <CardDescription>
                Tehdit modellemesi için önemli olduğu hâlde dokümanda
                yazmayanlar.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {draft.unknowns.length === 0 ? (
                <p className="text-xs text-muted-foreground">Kayıt yok.</p>
              ) : (
                <ul className="space-y-2">
                  {draft.unknowns.map((item, index) => (
                    <li key={index} className="rounded-md border border-border p-2.5">
                      <p className="text-xs">{item.text}</p>
                      {item.impact ? (
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          Önemi: {item.impact}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Lightbulb className="h-4 w-4 text-accent" aria-hidden />
                Varsayımlar ({draft.assumptions.length})
              </CardTitle>
              <CardDescription>
                Dokümanda açıkça yazmayan ama modele girmiş çıkarımlar.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {draft.assumptions.length === 0 ? (
                <p className="text-xs text-muted-foreground">Kayıt yok.</p>
              ) : (
                <ul className="space-y-2">
                  {draft.assumptions.map((item, index) => (
                    <li key={index} className="rounded-md border border-border p-2.5">
                      <p className="text-xs">{item.text}</p>
                      {item.reason ? (
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          Gerekçe: {item.reason}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-sm">Veri sınıfları ve roller</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {draft.data_classes.map((item) => (
                <Badge key={item.name} variant="outline">
                  {item.name} · {SENSITIVITY_LABELS[item.sensitivity] ?? item.sensitivity}
                </Badge>
              ))}
              {draft.roles.map((item) => (
                <Badge key={item.name}>{item.name}</Badge>
              ))}
              {draft.data_classes.length === 0 && draft.roles.length === 0 ? (
                <p className="text-xs text-muted-foreground">Kayıt yok.</p>
              ) : null}
            </CardContent>
          </Card>
        </div>
      ) : null}

      {selectedComponent || selectedFlow ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              {selectedComponent
                ? selectedComponent.name
                : `${nameOf(draft, selectedFlow!.source_id)} → ${nameOf(
                    draft,
                    selectedFlow!.target_id,
                  )}`}
            </CardTitle>
            <CardDescription>
              {selectedComponent?.description ??
                selectedFlow?.description ??
                "Dokümandan alınan kanıt alıntıları aşağıdadır."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {selectedComponent ? (
              <dl className="grid gap-3 text-xs sm:grid-cols-4">
                <Field label="Tür">
                  {COMPONENT_TYPE_LABELS[selectedComponent.type]}
                </Field>
                <Field label="Güven bölgesi">
                  {selectedComponent.trust_zone ?? "Belirtilmemiş"}
                </Field>
                <Field label="İnternete açık">
                  {maybeLabel(selectedComponent.internet_facing)}
                </Field>
                <Field label="Kimlik doğrulama">
                  {selectedComponent.authentication ?? "Belirtilmemiş"}
                </Field>
              </dl>
            ) : null}
            {selectedFlow ? (
              <dl className="grid gap-3 text-xs sm:grid-cols-4">
                <Field label="Protokol">{selectedFlow.protocol ?? "Belirtilmemiş"}</Field>
                <Field label="Şifreli">{maybeLabel(selectedFlow.encrypted)}</Field>
                <Field label="Kimlik doğrulamalı">
                  {maybeLabel(selectedFlow.authenticated)}
                </Field>
                <Field label="Veri sınıfları">
                  {selectedFlow.data_classes.join(", ") || "—"}
                </Field>
              </dl>
            ) : null}
            <EvidenceView
              evidence={(selectedComponent ?? selectedFlow)!.evidence}
              documents={documents}
            />
          </CardContent>
        </Card>
      ) : (
        <p className="text-xs text-muted-foreground">
          Diyagramdan ya da tablolardan bir öğe seçin; kanıt alıntısı ve
          dokümandaki yeri burada görünür.
        </p>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function nameOf(model: SystemModelData, id: string): string {
  return model.components.find((item) => item.id === id)?.name ?? id;
}

function parseMaybe(value: string): MaybeBool {
  if (value === "true") return true;
  if (value === "false") return false;
  return "unknown";
}
