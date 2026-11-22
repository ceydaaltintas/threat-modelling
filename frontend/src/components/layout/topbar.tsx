"use client";

import { Moon, Sun, UserCog } from "lucide-react";

import { useMeta } from "@/components/providers/meta-provider";
import { ROLE_LABELS, useRole } from "@/components/providers/role-provider";
import { useTheme } from "@/components/providers/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DemoRole } from "@/lib/types";

export function Topbar() {
  const { theme, toggle } = useTheme();
  const { role, setRole } = useRole();
  const { meta } = useMeta();

  const replayOn = meta?.demo_replay && meta.demo_replay !== "false";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-border bg-surface px-5">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="font-medium text-foreground md:hidden">
          {meta?.app_name ?? "Tehdit Modelleme Platformu"}
        </span>
        {/* Only state what changes how the product behaves right now. */}
        {replayOn ? (
          <Badge
            variant="accent"
            title="LLM yanıtları daha önce kaydedilmiş çağrılardan geliyor; yeni çağrı yapılmıyor."
          >
            Kayıtlı çıktı
          </Badge>
        ) : null}
      </div>

      <div className="flex items-center gap-2">
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <UserCog className="h-4 w-4" aria-hidden />
          <span className="sr-only">Rol seç</span>
          <select
            value={role}
            onChange={(event) => setRole(event.target.value as DemoRole)}
            className="h-8 rounded-md border border-input bg-surface px-2 text-xs text-foreground"
          >
            {(Object.keys(ROLE_LABELS) as DemoRole[]).map((value) => (
              <option key={value} value={value}>
                {ROLE_LABELS[value]}
              </option>
            ))}
          </select>
        </label>

        <Button
          variant="ghost"
          size="icon"
          onClick={toggle}
          aria-label={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
          title={theme === "dark" ? "Açık tema" : "Koyu tema"}
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" aria-hidden />
          ) : (
            <Moon className="h-4 w-4" aria-hidden />
          )}
        </Button>
      </div>
    </header>
  );
}
