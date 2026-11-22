"use client";

import * as React from "react";

import { api, eventStreamUrl } from "@/lib/api";
import type {
  ProgressEvent,
  Run,
  RunStatus,
  RunStep,
  StepStatus,
} from "@/lib/types";

export interface LlmUsage {
  calls: number;
  cached: number;
  tokens: number;
  replay: boolean;
}

export interface PauseState {
  step: number;
  reason: string;
  message: string;
}

export interface RunStreamState {
  run: Run | null;
  steps: RunStep[];
  status: RunStatus | "connecting";
  events: ProgressEvent[];
  llm: LlmUsage;
  pause: PauseState | null;
  /** True while the backend is sending phase-0 placeholder data. */
  placeholder: boolean;
  connected: boolean;
  error: string | null;
  reload: () => void;
  /** Re-read the step rows (counters and panel payload) from the API. */
  refreshSteps: () => Promise<void>;
}

const EMPTY_LLM: LlmUsage = { calls: 0, cached: 0, tokens: 0, replay: false };
const MAX_EVENTS = 300;

/**
 * Subscribes to the backend's SSE stream and keeps the stepper in sync.
 *
 * Step transitions come from real events only - nothing here animates on a
 * timer. On connect, the backend replays the events emitted so far, so a page
 * reload shows the correct state immediately.
 */
export function useRunStream(runId: string | null): RunStreamState {
  const [run, setRun] = React.useState<Run | null>(null);
  const [steps, setSteps] = React.useState<RunStep[]>([]);
  const [status, setStatus] = React.useState<RunStatus | "connecting">(
    "connecting",
  );
  const [events, setEvents] = React.useState<ProgressEvent[]>([]);
  const [llm, setLlm] = React.useState<LlmUsage>(EMPTY_LLM);
  const [pause, setPause] = React.useState<PauseState | null>(null);
  const [placeholder, setPlaceholder] = React.useState(false);
  const [connected, setConnected] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [tick, setTick] = React.useState(0);
  // Steps that have reported a terminal status. Their panel payload only
  // exists in the database, so each completion triggers one snapshot fetch.
  const [settled, setSettled] = React.useState("");

  // Initial snapshot from the database, so the step list exists before the
  // first event arrives.
  React.useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    api
      .run(runId)
      .then((value) => {
        if (cancelled) return;
        setRun(value);
        setSteps(value.steps);
        setStatus(value.status);
        setError(null);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [runId, tick]);

  const applyEvent = React.useCallback((event: ProgressEvent) => {
    if (event.placeholder) setPlaceholder(true);

    if (
      event.type === "step" &&
      event.step &&
      (event.status === "done" || event.status === "failed")
    ) {
      // Remember it; the effect below pulls the step's output.
      setSettled((current) =>
        current.includes(`|${event.step}:${event.status}`)
          ? current
          : `${current}|${event.step}:${event.status}`,
      );
    }

    if (event.type === "step" && event.step) {
      setSteps((current) =>
        current.map((step) =>
          step.step_no === event.step
            ? {
                ...step,
                status: (event.status as StepStatus) ?? step.status,
                progress: event.progress ?? step.progress,
                message: event.message ?? step.message,
                counters:
                  event.counters && Object.keys(event.counters).length > 0
                    ? event.counters
                    : step.counters,
                started_at: event.started_at ?? step.started_at,
                finished_at: event.finished_at ?? step.finished_at,
              }
            : step,
        ),
      );
    }

    if (event.type === "run" && event.status) {
      setStatus(event.status as RunStatus);
    }

    if (event.type === "pause" && event.step) {
      setPause({
        step: event.step,
        reason: event.reason ?? "user_action",
        message: event.message ?? "Kullanıcı işlemi bekleniyor.",
      });
      setStatus("waiting_user");
    }

    if (event.type === "resume" || event.type === "pause_skipped") {
      setPause(null);
      // Clearing the pause is not enough: the run is running again, and the
      // status badge must say so even if the run event is missed.
      setStatus((current) => (current === "waiting_user" ? "running" : current));
    }

    if (event.type === "step" && event.status === "waiting_user" && event.step) {
      setStatus("waiting_user");
    }

    if (event.llm && Object.keys(event.llm).length > 0) {
      setLlm((current) => ({
        calls: event.llm?.calls ?? current.calls,
        cached: event.llm?.cached ?? current.cached,
        tokens: event.llm?.tokens ?? current.tokens,
        replay: event.llm?.replay ?? current.replay,
      }));
    }

    setEvents((current) => {
      const next = [...current, event];
      return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
    });
  }, []);

  /**
   * Pull the authoritative step rows after each completion.
   *
   * The event stream carries progress, not payloads: a step's ``output``
   * (retrieved knowledge, risk distribution, report files) can be large and
   * lives in the database. Without this, every panel that reads ``output``
   * stays empty until the page is reloaded.
   */
  const refreshSteps = React.useCallback(async () => {
    if (!runId) return;
    try {
      const value = await api.run(runId);
      setSteps((current) =>
        current.map((step) => {
          const fresh = value.steps.find(
            (item) => item.step_no === step.step_no,
          );
          if (!fresh) return step;
          return {
            ...step,
            output: fresh.output ?? step.output,
            counters: fresh.counters ?? step.counters,
          };
        }),
      );
      setRun(value);
    } catch {
      /* the stream keeps working; the panel fills on the next completion */
    }
  }, [runId]);

  React.useEffect(() => {
    if (!settled) return;
    void refreshSteps();
  }, [settled, refreshSteps]);

  React.useEffect(() => {
    if (!runId) return;
    setEvents([]);
    const source = new EventSource(eventStreamUrl(runId));

    source.onopen = () => {
      setConnected(true);
      setError(null);
    };

    source.addEventListener("progress", (message) => {
      try {
        applyEvent(JSON.parse((message as MessageEvent).data) as ProgressEvent);
      } catch {
        /* malformed frame: ignore rather than break the stream */
      }
    });

    source.onerror = () => {
      setConnected(false);
      // EventSource reconnects on its own; the backlog replay then restores
      // the current state.
    };

    return () => {
      source.close();
      setConnected(false);
    };
  }, [runId, applyEvent, tick]);

  return React.useMemo(
    () => ({
      run,
      steps,
      status,
      events,
      llm,
      pause,
      placeholder,
      connected,
      error,
      reload: () => setTick((value) => value + 1),
      refreshSteps,
    }),
    [
      run,
      steps,
      status,
      events,
      llm,
      pause,
      placeholder,
      connected,
      error,
      refreshSteps,
    ],
  );
}
