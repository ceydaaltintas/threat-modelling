"use client";

import { Lock } from "lucide-react";
import * as React from "react";

import { useMeta } from "@/components/providers/meta-provider";
import { ROLE_LABELS, useRole } from "@/components/providers/role-provider";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { DemoRole, ReplayStatus } from "@/lib/types";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/60 py-2 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-right text-sm">{children}</span>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      <div className="rounded-md border border-border bg-surface px-3">
        {children}
      </div>
    </section>
  );
}

export default function SettingsPage() {
  const { meta } = useMeta();
  const { role, setRole } = useRole();
  const [replay, setReplay] = React.useState<ReplayStatus | null>(null);

  React.useEffect(() => {
    api.replayStatus().then(setReplay).catch(() => setReplay(null));
  }, []);

  return (
    <div className="mx-auto w-full max-w-2xl space-y-5 py-2">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Ayarlar</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Ortam değişkenlerinden okunur; API anahtarı gösterilmez.
        </p>
      </div>

      <Section title="Dil modeli">
        <Row label="Sağlayıcı">{meta?.llm_provider ?? "—"}</Row>
        <Row label="Model">
          {meta?.llm_model || (
            <span className="text-muted-foreground">tanımsız</span>
          )}
        </Row>
        <Row label="API anahtarı">
          <span className="flex items-center justify-end gap-1.5">
            <Lock className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
            {meta?.llm_configured ? (
              <Badge variant="success">Tanımlı</Badge>
            ) : (
              <Badge variant="warning">Tanımsız</Badge>
            )}
          </span>
        </Row>
      </Section>

      <Section title="Kayıtlı çıktı">
        <Row label="Mod">
          {replay?.mode === "strict" ? (
            <Badge variant="warning">strict</Badge>
          ) : replay?.mode === "true" ? (
            <Badge variant="accent">açık</Badge>
          ) : (
            <Badge>kapalı</Badge>
          )}
        </Row>
        <Row label="Kayıtlı yanıt">
          {replay ? (
            replay.ready ? (
              <Badge variant="success">{replay.recorded_calls}</Badge>
            ) : (
              <Badge variant="warning">yok</Badge>
            )
          ) : (
            "—"
          )}
        </Row>
      </Section>
      {replay && !replay.ready && replay.mode !== "false" ? (
        <p className="-mt-3 text-xs text-muted-foreground">
          Kayıt yok; çağrılar canlı yapılır. Kayıt üretmek için:{" "}
          <code className="rounded bg-surface-muted px-1">
            docker compose exec backend python -m scripts.seed_demo
          </code>
        </p>
      ) : null}

      <Section title="Risk eşikleri">
        <Row label="Düşük">≤ {meta?.risk_thresholds.low ?? "—"}</Row>
        <Row label="Orta">≤ {meta?.risk_thresholds.medium ?? "—"}</Row>
        <Row label="Yüksek">≤ {meta?.risk_thresholds.high ?? "—"}</Row>
        <Row label="Kritik">&gt; {meta?.risk_thresholds.high ?? "—"}</Row>
      </Section>

      <Section title="Rol">
        <div className="py-2">
          {(Object.keys(ROLE_LABELS) as DemoRole[]).map((value) => (
            <label key={value} className="flex items-center gap-2 py-1 text-sm">
              <input
                type="radio"
                name="role"
                checked={role === value}
                onChange={() => setRole(value)}
                className="h-4 w-4"
              />
              {ROLE_LABELS[value]}
            </label>
          ))}
          <p className="mt-1 text-[11px] text-muted-foreground">
            Gerçek SSO değildir; gerçek üründe kurumun kimlik sistemi buraya
            bağlanır.
          </p>
        </div>
      </Section>

      <p className="text-[11px] text-muted-foreground">
        Ücretsiz LLM katmanlarında gönderilen veri sağlayıcı tarafından
        kullanılabilir. Bu platformda yalnızca kurgusal örnek dokümanlar
        kullanın; gerçek müşteri verisi yüklemeyin.
        {meta?.ocr_enabled ? " OCR açık." : ""}
      </p>
    </div>
  );
}
