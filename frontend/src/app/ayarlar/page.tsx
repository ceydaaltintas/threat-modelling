"use client";

import { Database, Info, Lock } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { useMeta } from "@/components/providers/meta-provider";
import { ROLE_LABELS, useRole } from "@/components/providers/role-provider";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";
import type { DemoRole, ReplayStatus } from "@/lib/types";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/60 py-2.5 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-right text-sm">{children}</span>
    </div>
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
    <>
      <PageHeader
        title="Ayarlar"
        description="Ortam değişkenlerinden okunur; API anahtarı gösterilmez."
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>LLM sağlayıcı</CardTitle>
            <CardDescription>
              Varsayılan öneri Gemini&apos;nin yerel istemcisidir; yapılandırılmış
              çıktı ve görsel/PDF girdisi daha güvenilirdir.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Row label="Sağlayıcı">{meta?.llm_provider ?? "—"}</Row>
            <Row label="Model">
              {meta?.llm_model || (
                <span className="text-muted-foreground">
                  README&apos;den seçilecek
                </span>
              )}
            </Row>
            <Row label="API anahtarı">
              <span className="flex items-center justify-end gap-1.5">
                <Lock className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                {meta?.llm_configured ? (
                  <Badge variant="success">Tanımlı (gösterilmez)</Badge>
                ) : (
                  <Badge variant="warning">Tanımsız</Badge>
                )}
              </span>
            </Row>
            <Row label="Kayıtlı çıktı modu">{meta?.demo_replay ?? "—"}</Row>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-4 w-4 text-accent" aria-hidden />
              Kayıtlı çıktı
            </CardTitle>
            <CardDescription>
              Kayıtlı çıktı, daha önce gerçekten yapılmış LLM çağrılarının
              yanıtlarıdır; elle yazılmış kayıt yoktur. Demoyu internetsiz
              çalıştırmayı sağlar.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Row label="Mod">
              {replay?.mode === "strict" ? (
                <Badge variant="warning">strict — kayıt yoksa hata verir</Badge>
              ) : replay?.mode === "true" ? (
                <Badge variant="accent">true — kayıt varsa kullanılır</Badge>
              ) : (
                <Badge>false — her zaman canlı çağrı</Badge>
              )}
            </Row>
            <Row label="Kayıtlı yanıt">
              {replay ? (
                replay.ready ? (
                  <Badge variant="success">{replay.recorded_calls} kayıt</Badge>
                ) : (
                  <Badge variant="warning">Kayıt yok</Badge>
                )
              ) : (
                "—"
              )}
            </Row>
            {replay && Object.keys(replay.by_sample).length > 0 ? (
              <Row label="Örnek senaryo kaydı">
                <span className="flex flex-wrap justify-end gap-1">
                  {Object.entries(replay.by_sample).map(([key, count]) => (
                    <Badge key={key} variant="outline">
                      {key}: {count}
                    </Badge>
                  ))}
                </span>
              </Row>
            ) : null}
            {replay && !replay.ready ? (
              <p className="mt-2 text-xs text-muted-foreground">
                Kayıt üretmek için bir kez, internet ve anahtar varken:{" "}
                <code>
                  docker compose exec backend python -m scripts.seed_demo
                </code>
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Risk eşikleri</CardTitle>
            <CardDescription>
              Olasılık × etki (1–25). Skor bu eşiklere göre seviyeye çevrilir.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Row label="Düşük">≤ {meta?.risk_thresholds.low ?? "—"}</Row>
            <Row label="Orta">≤ {meta?.risk_thresholds.medium ?? "—"}</Row>
            <Row label="Yüksek">≤ {meta?.risk_thresholds.high ?? "—"}</Row>
            <Row label="Kritik">
              &gt; {meta?.risk_thresholds.high ?? "—"}
            </Row>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Doküman okuma</CardTitle>
          </CardHeader>
          <CardContent>
            <Row label="OCR">
              {meta?.ocr_enabled ? (
                <Badge variant="accent">Açık</Badge>
              ) : (
                <Badge>Kapalı (varsayılan)</Badge>
              )}
            </Row>
            <Row label="Ürün adı">{meta?.app_name ?? "—"}</Row>
            <Row label="Ortam">{meta?.app_env ?? "—"}</Row>
            <Row label="Yapı aşaması">Aşama {meta?.build_phase ?? "—"}</Row>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Rol (demo)</CardTitle>
            <CardDescription>
              Gerçek SSO değildir. Gerçek üründe kurumun kimlik sisteminin
              bağlanacağı yer burasıdır.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {(Object.keys(ROLE_LABELS) as DemoRole[]).map((value) => (
              <label key={value} className="flex items-center gap-2 text-sm">
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
          </CardContent>
        </Card>
      </div>

      <Card className="border-level-high/40 bg-level-high/5">
        <CardContent className="flex gap-3 pt-5 text-sm">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-level-high" aria-hidden />
          <div className="space-y-1">
            <p className="font-medium">Ücretsiz LLM katmanı uyarısı</p>
            <p className="text-muted-foreground">
              Ücretsiz katmanda gönderilen veri sağlayıcı tarafından
              kullanılabilir. Bu nedenle bu platformda yalnızca kurgusal örnek
              dokümanlar kullanılır; gerçek banka verisi yüklenmemelidir.
            </p>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
