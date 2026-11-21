"use client";

import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

type ToastTone = "info" | "success" | "error";

interface Toast {
  id: number;
  title: string;
  description?: string;
  tone: ToastTone;
}

interface ToastContextValue {
  toast: (input: {
    title: string;
    description?: string;
    tone?: ToastTone;
  }) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

const TONE_ICON = {
  info: Info,
  success: CheckCircle2,
  error: TriangleAlert,
} as const;

const TONE_CLASS: Record<ToastTone, string> = {
  info: "border-border",
  success: "border-level-low/50",
  error: "border-level-critical/50",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);
  const nextId = React.useRef(1);

  const dismiss = React.useCallback((id: number) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const toast = React.useCallback<ToastContextValue["toast"]>(
    ({ title, description, tone = "info" }) => {
      const id = nextId.current++;
      setToasts((current) => [...current, { id, title, description, tone }]);
      window.setTimeout(() => dismiss(id), 6000);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2"
        role="region"
        aria-label="Bildirimler"
      >
        {toasts.map((item) => {
          const Icon = TONE_ICON[item.tone];
          return (
            <div
              key={item.id}
              role="status"
              className={cn(
                "pointer-events-auto flex items-start gap-3 rounded-lg border bg-surface p-3 shadow-lg",
                TONE_CLASS[item.tone],
              )}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{item.title}</p>
                {item.description ? (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {item.description}
                  </p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => dismiss(item.id)}
                className="rounded p-0.5 text-muted-foreground hover:bg-surface-muted"
                aria-label="Bildirimi kapat"
              >
                <X className="h-3.5 w-3.5" aria-hidden />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return context;
}
