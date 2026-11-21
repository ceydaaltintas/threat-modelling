import type { LucideIcon } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

/** Shared empty state: icon, Turkish headline, explanation and one action. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-surface px-6 py-14 text-center",
        className,
      )}
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-surface-muted text-muted-foreground">
        <Icon className="h-5 w-5" aria-hidden />
      </span>
      <div className="space-y-1">
        <p className="text-sm font-semibold">{title}</p>
        <p className="mx-auto max-w-md text-sm text-muted-foreground">
          {description}
        </p>
      </div>
      {action}
    </div>
  );
}
