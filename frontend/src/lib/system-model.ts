// The system model as the backend returns it, plus UI helpers.
// Field names are English (they mirror the backend schema); every label the
// user sees is Turkish.

export type MaybeBool = boolean | "unknown";

export type ComponentType =
  | "web_app"
  | "mobile_app"
  | "api"
  | "service"
  | "database"
  | "queue"
  | "external"
  | "gateway"
  | "auth"
  | "admin"
  | "llm"
  | "other";

export interface Evidence {
  quote: string;
  page: number | null;
  section: string | null;
}

export interface SmComponent {
  id: string;
  name: string;
  type: ComponentType;
  technology: string | null;
  trust_zone: string | null;
  internet_facing: MaybeBool;
  authentication: string | null;
  description: string | null;
  evidence: Evidence[];
}

export interface SmFlow {
  id: string;
  source_id: string;
  target_id: string;
  protocol: string | null;
  encrypted: MaybeBool;
  authenticated: MaybeBool;
  data_classes: string[];
  description: string | null;
  evidence: Evidence[];
}

export interface SmTrustZone {
  id: string;
  name: string;
  description: string | null;
}

export interface SmDataClass {
  name: string;
  sensitivity: "low" | "medium" | "high" | "unknown";
  description: string | null;
}

export interface SmRole {
  name: string;
  permissions: string | null;
}

export interface SmAssumption {
  text: string;
  reason: string | null;
}

export interface SmUnknown {
  text: string;
  impact: string | null;
}

export interface SystemModelData {
  components: SmComponent[];
  data_flows: SmFlow[];
  trust_zones: SmTrustZone[];
  data_classes: SmDataClass[];
  roles: SmRole[];
  assumptions: SmAssumption[];
  unknowns: SmUnknown[];
}

export interface SystemModelVersion {
  id: string;
  run_id: string;
  version: number;
  source: "ai" | "expert";
  data: SystemModelData;
  approved_at: string | null;
  approved_by: string | null;
  created_at: string;
}

export const COMPONENT_TYPE_LABELS: Record<ComponentType, string> = {
  web_app: "Web uygulaması",
  mobile_app: "Mobil uygulama",
  api: "API",
  service: "Servis",
  database: "Veritabanı",
  queue: "Kuyruk",
  external: "Dış sistem",
  gateway: "Ağ geçidi",
  auth: "Kimlik doğrulama",
  admin: "Yönetim paneli",
  llm: "Yapay zekâ / LLM",
  other: "Diğer",
};

export const SENSITIVITY_LABELS: Record<string, string> = {
  low: "Düşük",
  medium: "Orta",
  high: "Yüksek",
  unknown: "Belirtilmemiş",
};

/** "Evet" / "Hayır" / "Belirtilmemiş" — never a bare boolean in the UI. */
export function maybeLabel(value: MaybeBool): string {
  if (value === true) return "Evet";
  if (value === false) return "Hayır";
  return "Belirtilmemiş";
}

export const EMPTY_MODEL: SystemModelData = {
  components: [],
  data_flows: [],
  trust_zones: [],
  data_classes: [],
  roles: [],
  assumptions: [],
  unknowns: [],
};

/** A flow the document says is unencrypted or unauthenticated. */
export function flowIsRisky(flow: SmFlow): boolean {
  return flow.encrypted === false || flow.authenticated === false;
}

/** A flow where the document simply does not say. */
export function flowIsUnknown(flow: SmFlow): boolean {
  return flow.encrypted === "unknown" || flow.authenticated === "unknown";
}

export function zoneOf(component: SmComponent): string {
  return component.trust_zone?.trim() || "Belirtilmemiş bölge";
}
