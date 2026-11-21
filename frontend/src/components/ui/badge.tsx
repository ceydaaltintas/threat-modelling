import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "border-border bg-surface-muted text-muted-foreground",
        accent: "border-accent/30 bg-accent-subtle text-accent",
        outline: "border-border text-foreground",
        success: "border-level-low/40 bg-level-low/10 text-level-low",
        warning: "border-level-high/40 bg-level-high/10 text-level-high",
        danger:
          "border-level-critical/40 bg-level-critical/10 text-level-critical",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
