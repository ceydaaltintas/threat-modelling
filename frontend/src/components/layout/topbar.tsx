"use client";

import { Moon, Sun, UserCog } from "lucide-react";
import * as React from "react";

import { useMeta } from "@/components/providers/meta-provider";
import { ROLE_LABELS, useRole } from "@/components/providers/role-provider";
import { useTheme } from "@/components/providers/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { DemoRole, ReplayStatus } from "@/lib/types";

export function Topbar() {
  const { theme, toggle } = useTheme();
  const { role, setRole } = useRole();
  const { meta } = useMeta();
  const [replay, setReplay] = React.useState<ReplayStatus | null>(null);

  const replayOn = meta?.demo_replay && meta.demo_replay !== "false";

  React.useEffect(() => {
    if (!replayOn) return;
    api.replayStatus().then(setReplay).catch(() => setReplay(null));
  }, [replayOn]);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-border bg-surface px-5">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="font-medium text-foreground md:hidden">
          {meta?.app_name ?? "Tehdit Modelleme Platformu"}
        </span>
        {/* Only state what changes how the product behaves right now - and
            say plainly when the mode is on but there is nothing recorded, so
            nobody thinks the demo is running offline when it is not. */}
        {replayOn && replay ? (
          replay.ready ? (
            <Badge
              variant="accent"
              title={`${replay.recorded_calls} kayıtlı yanıt var; aynı istem tekrar sorulmaz.`}
            >
              Kayıtlı çıktı · {replay.recorded_calls}
            </Badge>
          ) : (
            <Badge
              variant="warning"
              title="Kayıtlı çıktı modu açık ama henüz kayıt yok; çağrılar canlı yapılır. scripts/seed_demo.py ile kayıt üretebilirsiniz."
            >
              Kayıt yok · canlı çağrı
            </Badge>
          )
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
