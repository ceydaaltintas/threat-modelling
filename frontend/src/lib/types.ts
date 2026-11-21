import type { Level } from "@/lib/levels";

// Shapes returned by the backend API.

export type StepStatus =
  | "pending"
  | "running"
  | "done"
  | "failed"
  | "waiting_user"
  | "skipped";

export type RunStatus =
  | "pending"
  | "running"
  | "waiting_user"
  | "done"
  | "failed"
  | "cancelled";

export type Performer = "code" | "llm" | "code+llm" | "human";

export interface StepInfo {
  no: number;
  name: string;
  description: string;
  performer: Performer;
  counter_labels: Record<string, string>;
}

export interface Meta {
  app_name: string;
  app_env: string;
  version: string;
  build_phase: number;
  steps: StepInfo[];
  model_approval_after_step: number;
  risk_thresholds: { low: number; medium: number; high: number };
  demo_replay: string;
  ocr_enabled: boolean;
  llm_provider: string;
  llm_model: string;
  llm_configured: boolean;
}

export interface SampleScenario {
  key: string;
  title: string;
  doc_code: string;
  summary: string;
  focus: string;
  filename: string;
  available: boolean;
  size_bytes: number | null;
}

export interface RunStep {
  step_no: number;
  name: string;
  status: StepStatus;
  progress: number;
  started_at: string | null;
  finished_at: string | null;
  counters: Record<string, number> | null;
  message: string | null;
  /** Step specific payload for its detail panel. */
  output: Record<string, unknown> | null;
}

export interface Run {
  id: string;
  project_id: string;
  project_name: string | null;
  status: RunStatus;
  started_at: string | null;
  finished_at: string | null;
  demo_replay: string;
  auto_continue: boolean;
  error_message: string | null;
  steps: RunStep[];
}

export interface ProjectRow {
  id: string;
  name: string;
  description: string | null;
  sample_key: string | null;
  created_at: string;
  last_run: {
    id: string;
    status: RunStatus;
    started_at: string | null;
    finished_at: string | null;
  } | null;
  risk_summary: { critical: number; high: number };
}

/** One event from the SSE stream. */
export interface ProgressEvent {
  run_id: string;
  ts: string;
  type: "run" | "step" | "pause" | "pause_skipped" | "resume";
  step?: number;
  step_name?: string;
  status?: string;
  progress?: number;
  message?: string | null;
  reason?: string;
  counters?: Record<string, number>;
  started_at?: string | null;
  finished_at?: string | null;
  llm?: { calls?: number; cached?: number; tokens?: number; replay?: boolean };
  /** True while the backend is still serving phase-0 placeholder data. */
  placeholder?: boolean;
}

export interface SectionMapEntry {
  type: "page" | "section";
  page: number;
  start: number;
  end: number;
  number?: string;
  title?: string;
  label?: string;
}

export interface DocumentOut {
  id: string;
  filename: string;
  doc_type: string;
  size_bytes: number | null;
  page_count: number | null;
  extraction_note: string | null;
  section_map: SectionMapEntry[] | null;
  raw_text: string | null;
}

export interface AuditEntry {
  id: string;
  at: string;
  actor: string;
  actor_role: string;
  action: string;
  object_type: string;
  object_id: string | null;
  run_id: string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  reason: string | null;
}

export interface KbStats {
  total_chunks: number;
  by_source: Record<string, number>;
  loaded: boolean;
  verification_needed: number;
  licenses: Record<string, string>;
  embedding_model: string;
  vector_search: boolean;
}

export interface KbHit {
  id: string;
  source: string;
  identifier: string;
  title: string;
  text: string;
  url: string | null;
  license: string | null;
  verification: string | null;
  score: number;
  matched_by: string[];
}

export interface KbSearchResult {
  query: string;
  diagnostics: {
    mode: string;
    exact_identifiers: string[];
    vector_search: boolean;
    candidates: number;
    note: string | null;
  };
  results: KbHit[];
}

export interface KnowledgeSource {
  id: string;
  title?: string | null;
  url?: string | null;
}

export interface ThreatRow {
  id: string;
  source: "rule" | "llm" | "merged";
  rule_id: string | null;
  component_ref: string | null;
  flow_ref: string | null;
  stride: "S" | "T" | "R" | "I" | "D" | "E";
  title: string;
  description: string | null;
  scenario: string | null;
  evidence: Array<{ quote: string; page: number | null; section: string | null }>;
  knowledge_sources: KnowledgeSource[];
  ai_proposed: {
    likelihood: number | null;
    impact: number | null;
    rationale: string | null;
  } | null;
  system_calc: {
    likelihood: number;
    impact: number;
    score: number;
    level: Level;
    base_likelihood: number;
    base_impact: number;
    breakdown: Array<{
      label: string;
      field: "likelihood" | "impact";
      delta: number;
      reason: string;
    }>;
    explanation: string;
  } | null;
  expert: {
    status?: string;
    by?: string;
    at?: string;
    note?: string | null;
    reason?: string | null;
    likelihood?: number;
    impact?: number;
    score?: number;
    level?: string;
    bulk?: boolean;
  } | null;
  mitigations: Array<{
    id: string;
    title?: string;
    text?: string;
    effort?: string;
    source?: "catalog" | "llm";
  }>;
  control_mappings: Array<{
    framework: string;
    id: string;
    verification: "needed" | "confirmed";
    via: string;
  }>;
  validation_notes: Array<{
    code: string;
    label?: string;
    detail?: string | null;
    severity?: "error" | "warning" | "info";
  }>;
  validation_status: string;
  review_status: string;
  is_assumption: boolean;
  rule_context: {
    base_likelihood: number;
    base_impact: number;
    confidence?: "confirmed" | "possible";
    internet_facing: boolean;
    sensitive_data: boolean;
    data_classes: string[];
    control_evidence: string | null;
    area: string;
  } | null;
}

export interface ThreatListResponse {
  total: number;
  summary: {
    by_source: Record<string, number>;
    by_stride: Record<string, number>;
    by_level?: Record<string, number>;
    assumptions: number;
    flagged?: number;
  };
  threats: ThreatRow[];
}

/** Step 8's stored panel payload. */
export interface ReviewOutput {
  total: number;
  pending: number;
  accepted: number;
  rejected: number;
  false_positive: number;
  edited: number;
  decided: number;
}

/** Step 9's stored panel payload. */
export interface ReportOutput {
  files: Array<{ kind: string; name: string; size: number }>;
  summary_text: string | null;
  summary_is_ai: boolean;
  counts: Record<string, number>;
  by_level: Record<string, number>;
  by_stride: Record<string, number>;
  by_component: Array<[string, number]>;
  heatmap: Record<string, number>;
  thresholds: { low: number; medium: number; high: number };
  top_threats: Array<{
    id: string;
    title: string;
    level: string;
    score: number;
    component: string;
  }>;
  unknowns: Array<{ text: string; impact?: string | null }>;
}

export interface DashboardData {
  available: boolean;
  reason?: string;
  run?: {
    id: string;
    project: string;
    status: string;
    started_at: string | null;
    finished_at: string | null;
  };
  kpis?: {
    total: number;
    included: number;
    critical: number;
    high: number;
    assumptions: number;
    flagged: number;
    decided: number;
    decided_ratio: number;
    components: number;
    flows: number;
  };
  by_level?: Record<string, number>;
  by_stride?: Record<string, number>;
  by_component?: Array<[string, number]>;
  by_review?: Record<string, number>;
  heatmap?: Record<string, number>;
  thresholds?: { low: number; medium: number; high: number };
  top_threats?: Array<{
    id: string;
    title: string;
    level: string;
    score: number;
    component: string;
    stride: string;
  }>;
  unknowns?: Array<{ text: string; impact?: string | null }>;
}

export interface DashboardRun {
  id: string;
  created_at: string;
  status: string;
  project: string;
  threats: number;
}

export type ReviewAction =
  | "accept"
  | "reject"
  | "false_positive"
  | "edit"
  | "reset";

/** Step 5's stored panel payload. */
export interface ValidationOutput {
  checked: number;
  flagged: number;
  unknown_ids: number;
  duplicates: number;
  evidence_missing: number;
  note_labels: Record<string, string>;
}

/** Step 6's stored panel payload. */
export interface RiskOutput {
  by_level: Record<string, number>;
  heatmap: Record<string, number>;
  thresholds: { low: number; medium: number; high: number };
  ai_level_differs: number;
  total: number;
}

/** Step 7's stored panel payload. */
export interface MitigationOutput {
  threats: number;
  llm_calls: number;
  llm_written: number;
  control_mappings: number;
  unknown_mitigations: number;
  llm_note: string | null;
  llm_budget: number;
}

/** Step 3's stored panel payload. */
export interface RetrievalOutput {
  elements: Array<{
    kind: "component" | "flow";
    id: string;
    label: string;
    query: string;
    sources: KbHit[];
  }>;
  unique_identifiers: string[];
  degraded: boolean;
  note: string | null;
}

/** Step 4's stored panel payload. */
export interface ThreatGenOutput {
  rule_threats: number;
  llm_threats: number;
  merged_duplicates: number;
  total: number;
  llm_note: string | null;
  knowledge_ids_offered: number;
}

export type DemoRole = "security_expert" | "manager";
