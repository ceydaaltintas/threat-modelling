"use client";

import { LayoutDashboard } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { useMeta } from "@/components/providers/meta-provider";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { levelForScore, levelClasses } from "@/lib/levels";
import { cn } from "@/lib/utils";

const KPIS = [
  { key: "total", label: "Toplam tehdit" },
  { key: "critical", label: "Kritik" },
  { key: "high", label: "Yüksek" },
  { key: "approved", label: "Onaylanan" },
] as const;

const SCALE = [1, 2, 3, 4, 5];

export default function DashboardPage() {
  const { meta } = useMeta();
  const thresholds = meta?.risk_thresholds ?? { low: 4, medium: 9, high: 16 };

  return (
    <>
      <PageHeader
        title="Özet panosu"
        description="Analiz tamamlandığında tehdit dağılımı, risk ısı haritası ve en kritik bulgular burada görünür."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {KPIS.map((kpi) => (
          <Card key={kpi.key}>
            <CardContent className="pt-5">
              <p className="text-xs text-muted-foreground">{kpi.label}</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-muted-foreground">
                —
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>5×5 risk ısı haritası</CardTitle>
            <CardDescription>
              Olasılık × etki. Eşikler: ≤{thresholds.low} Düşük, ≤
              {thresholds.medium} Orta, ≤{thresholds.high} Yüksek, üzeri Kritik.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <div className="flex flex-col justify-between py-1 text-[10px] text-muted-foreground">
                {[...SCALE].reverse().map((value) => (
                  <span key={value} className="h-10 leading-10">
                    {value}
                  </span>
                ))}
              </div>
              <div className="flex-1">
                <div className="grid grid-cols-5 gap-1">
                  {[...SCALE].reverse().map((impact) =>
                    SCALE.map((likelihood) => {
                      const score = impact * likelihood;
                      const level = levelForScore(score, thresholds);
                      return (
                        <div
                          key={`${impact}-${likelihood}`}
                          title={`Olasılık ${likelihood} × Etki ${impact} = ${score} (${level})`}
                          className={cn(
                            "flex h-10 items-center justify-center rounded border text-[11px] font-medium",
                            levelClasses[level],
                          )}
                        >
                          0
                        </div>
                      );
                    }),
                  )}
                </div>
                <div className="mt-1 grid grid-cols-5 gap-1 text-center text-[10px] text-muted-foreground">
                  {SCALE.map((value) => (
                    <span key={value}>{value}</span>
                  ))}
                </div>
                <p className="mt-1 text-center text-[10px] text-muted-foreground">
                  Olasılık →
                </p>
              </div>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              Hücreler Aşama 4&apos;te gerçek tehdit sayılarıyla dolacak ve
              tıklandığında tehdit tablosunu filtreleyecek.
            </p>
          </CardContent>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>STRIDE dağılımı</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {[
                  ["S", "Kimlik taklidi"],
                  ["T", "Veri değiştirme"],
                  ["R", "İnkâr"],
                  ["I", "Bilgi sızması"],
                  ["D", "Hizmet kesintisi"],
                  ["E", "Yetki yükseltme"],
                ].map(([code, label]) => (
                  <Badge key={code} variant="outline">
                    {code} · {label} · —
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          <EmptyState
            icon={LayoutDashboard}
            title="Pano verisi için tamamlanmış bir analiz gerekiyor"
            description="Grafikler, en kritik 5 tehdit, durum dağılımı ve “dokümanda belirtilmeyen ama önemli” konular Aşama 4'te bağlanacak."
          />
        </div>
      </div>
    </>
  );
}
