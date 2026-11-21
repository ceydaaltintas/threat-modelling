"use client";

import * as React from "react";

import { api } from "@/lib/api";
import type { Meta } from "@/lib/types";

interface MetaContextValue {
  meta: Meta | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const MetaContext = React.createContext<MetaContextValue | null>(null);

/**
 * Loads backend metadata once (product name, the nine steps, thresholds).
 * The step list is never hard-coded in the UI.
 */
export function MetaProvider({ children }: { children: React.ReactNode }) {
  const [meta, setMeta] = React.useState<Meta | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [tick, setTick] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .meta()
      .then((value) => {
        if (!cancelled) {
          setMeta(value);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tick]);

  const value = React.useMemo<MetaContextValue>(
    () => ({ meta, loading, error, reload: () => setTick((t) => t + 1) }),
    [meta, loading, error],
  );

  return <MetaContext.Provider value={value}>{children}</MetaContext.Provider>;
}

export function useMeta(): MetaContextValue {
  const context = React.useContext(MetaContext);
  if (!context) throw new Error("useMeta must be used inside <MetaProvider>");
  return context;
}
