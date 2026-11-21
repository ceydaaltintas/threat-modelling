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
}

export type DemoRole = "security_expert" | "manager";
