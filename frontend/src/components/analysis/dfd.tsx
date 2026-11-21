"use client";

import {
  Bot,
  Boxes,
  Database,
  Globe,
  KeyRound,
  Layers,
  ListTree,
  Monitor,
  Network,
  Server,
  Settings2,
  Smartphone,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import * as React from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";

import {
  COMPONENT_TYPE_LABELS,
  flowIsRisky,
  flowIsUnknown,
  zoneOf,
  type ComponentType,
  type SmComponent,
  type SmFlow,
  type SystemModelData,
} from "@/lib/system-model";
import { cn } from "@/lib/utils";

import "reactflow/dist/style.css";

const TYPE_ICON: Record<ComponentType, LucideIcon> = {
  web_app: Monitor,
  mobile_app: Smartphone,
  api: Network,
  service: Server,
  database: Database,
  queue: Layers,
  external: Globe,
  gateway: Boxes,
  auth: KeyRound,
  admin: Settings2,
  llm: Bot,
  other: ListTree,
};

// Layout constants: one column per trust zone, components stacked inside.
const ZONE_WIDTH = 250;
const ZONE_GAP = 40;
const NODE_HEIGHT = 74;
const NODE_GAP = 16;
const ZONE_PADDING_TOP = 44;
const ZONE_PADDING_BOTTOM = 20;

interface ComponentNodeData {
  component: SmComponent;
  selected: boolean;
}

function ComponentNode({ data }: NodeProps<ComponentNodeData>) {
  const { component, selected } = data;
  const Icon = TYPE_ICON[component.type] ?? ListTree;
  return (
    <div
      className={cn(
        "w-[218px] rounded-md border bg-surface px-2.5 py-2 shadow-sm transition-colors",
        selected ? "border-accent ring-2 ring-accent/30" : "border-border",
        component.internet_facing === true && "border-level-high/60",
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-muted-foreground" />
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" aria-hidden />
        <div className="min-w-0">
          <p className="truncate text-[12px] font-medium leading-tight">
            {component.name}
          </p>
          <p className="truncate text-[10px] text-muted-foreground">
            {COMPONENT_TYPE_LABELS[component.type] ?? component.type}
            {component.technology ? ` · ${component.technology}` : ""}
          </p>
          {component.internet_facing === true ? (
            <p className="mt-0.5 text-[10px] font-medium text-level-high">
              İnternete açık
            </p>
          ) : null}
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-muted-foreground" />
    </div>
  );
}

function ZoneNode({ data }: NodeProps<{ label: string; count: number }>) {
  return (
    <div className="h-full w-full rounded-lg border border-dashed border-border bg-surface-muted/60">
      <p className="px-3 pt-2 text-[11px] font-medium text-muted-foreground">
        {data.label}
        <span className="ml-1 font-normal">({data.count})</span>
      </p>
    </div>
  );
}

const NODE_TYPES = { component: ComponentNode, zone: ZoneNode };

function buildGraph(
  model: SystemModelData,
  selectedId: string | null,
): { nodes: Node[]; edges: Edge[] } {
  const zones = new Map<string, SmComponent[]>();
  for (const component of model.components) {
    const zone = zoneOf(component);
    const list = zones.get(zone) ?? [];
    list.push(component);
    zones.set(zone, list);
  }

  const nodes: Node[] = [];
  let x = 0;

  for (const [zoneName, components] of zones) {
    const height =
      ZONE_PADDING_TOP +
      components.length * NODE_HEIGHT +
      Math.max(0, components.length - 1) * NODE_GAP +
      ZONE_PADDING_BOTTOM;

    nodes.push({
      id: `zone:${zoneName}`,
      type: "zone",
      position: { x, y: 0 },
      data: { label: zoneName, count: components.length },
      draggable: false,
      selectable: false,
      style: { width: ZONE_WIDTH, height, zIndex: -1 },
    });

    components.forEach((component, index) => {
      nodes.push({
        id: component.id,
        type: "component",
        position: {
          x: x + 16,
          y: ZONE_PADDING_TOP + index * (NODE_HEIGHT + NODE_GAP),
        },
        data: { component, selected: selectedId === component.id },
      });
    });

    x += ZONE_WIDTH + ZONE_GAP;
  }

  const known = new Set(model.components.map((component) => component.id));
  const edges: Edge[] = model.data_flows
    .filter((flow) => known.has(flow.source_id) && known.has(flow.target_id))
    .map((flow) => {
      const risky = flowIsRisky(flow);
      const unknown = !risky && flowIsUnknown(flow);
      const colour = risky
        ? "hsl(var(--level-critical))"
        : unknown
          ? "hsl(var(--level-medium))"
          : "hsl(var(--muted-foreground))";
      return {
        id: flow.id,
        source: flow.source_id,
        target: flow.target_id,
        label: edgeLabel(flow),
        animated: false,
        selected: selectedId === flow.id,
        style: {
          stroke: colour,
          strokeWidth: selectedId === flow.id ? 2.5 : 1.5,
          // Unencrypted / unauthenticated flows are dashed as well as coloured.
          strokeDasharray: risky || unknown ? "6 4" : undefined,
        },
        labelStyle: { fontSize: 10, fill: "hsl(var(--muted-foreground))" },
        labelBgStyle: { fill: "hsl(var(--surface))", fillOpacity: 0.9 },
        markerEnd: { type: MarkerType.ArrowClosed, color: colour, width: 16, height: 16 },
      } satisfies Edge;
    });

  return { nodes, edges };
}

function edgeLabel(flow: SmFlow): string {
  const parts: string[] = [];
  if (flow.protocol) parts.push(flow.protocol);
  if (flow.encrypted === false) parts.push("şifresiz");
  if (flow.authenticated === false) parts.push("kimliksiz");
  return parts.join(" · ");
}

export function Dfd({
  model,
  selectedId,
  onSelectComponent,
  onSelectFlow,
}: {
  model: SystemModelData;
  selectedId: string | null;
  onSelectComponent: (id: string) => void;
  onSelectFlow: (id: string) => void;
}) {
  const { nodes, edges } = React.useMemo(
    () => buildGraph(model, selectedId),
    [model, selectedId],
  );

  if (model.components.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center rounded-md border border-dashed border-border text-sm text-muted-foreground">
        Diyagram için bileşen bulunamadı.
      </div>
    );
  }

  return (
    <div className="h-[460px] w-full overflow-hidden rounded-md border border-border bg-surface">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.2}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        onNodeClick={(_, node) => {
          if (node.type === "component") onSelectComponent(node.id);
        }}
        onEdgeClick={(_, edge) => onSelectFlow(edge.id)}
      >
        <Background gap={18} size={1} color="hsl(var(--border))" />
        <Controls showInteractive={false} position="bottom-right" />
      </ReactFlow>
      <div className="flex flex-wrap items-center gap-4 border-t border-border px-3 py-2 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="h-0 w-6 border-t-2 border-muted-foreground" />
          Şifreli / kimlik doğrulamalı
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0 w-6 border-t-2 border-dashed border-level-medium" />
          Dokümanda belirtilmemiş
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0 w-6 border-t-2 border-dashed border-level-critical" />
          Şifresiz veya kimlik doğrulamasız
        </span>
      </div>
    </div>
  );
}
