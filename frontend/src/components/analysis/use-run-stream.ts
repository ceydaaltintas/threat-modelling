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
    }),
    [run, steps, status, events, llm, pause, placeholder, connected, error],
  );
}
