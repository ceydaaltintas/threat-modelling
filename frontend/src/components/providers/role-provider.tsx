"use client";

import * as React from "react";

import type { DemoRole } from "@/lib/types";

interface RoleContextValue {
  role: DemoRole;
  setRole: (role: DemoRole) => void;
  /** Managers get a read-only view of the demo. */
  readOnly: boolean;
  label: string;
}

const RoleContext = React.createContext<RoleContextValue | null>(null);
const STORAGE_KEY = "tm.role";

export const ROLE_LABELS: Record<DemoRole, string> = {
  security_expert: "Güvenlik Uzmanı",
  manager: "Yönetici (salt okunur)",
};

/**
 * Demo-only role switcher. This is NOT authentication: a real deployment
 * plugs the bank's own identity system in here (see README).
 */
export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = React.useState<DemoRole>("security_expert");

  React.useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "manager" || stored === "security_expert") {
        setRoleState(stored);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const setRole = React.useCallback((next: DemoRole) => {
    setRoleState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const value = React.useMemo<RoleContextValue>(
    () => ({
      role,
      setRole,
      readOnly: role === "manager",
      label: ROLE_LABELS[role],
    }),
    [role, setRole],
  );

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useRole(): RoleContextValue {
  const context = React.useContext(RoleContext);
  if (!context) throw new Error("useRole must be used inside <RoleProvider>");
  return context;
}
