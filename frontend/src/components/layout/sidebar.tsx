"use client";

import {
  BookOpen,
  FileSearch,
  LayoutDashboard,
  ListChecks,
  PlusCircle,
  ScrollText,
  Settings,
  ShieldHalf,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useMeta } from "@/components/providers/meta-provider";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Projeler", icon: ListChecks },
  { href: "/analiz/yeni", label: "Yeni analiz", icon: PlusCircle },
  { href: "/pano", label: "Özet panosu", icon: LayoutDashboard },
  { href: "/bilgi-tabani", label: "Bilgi tabanı", icon: BookOpen },
  { href: "/denetim", label: "Denetim izi", icon: ScrollText },
  { href: "/ayarlar", label: "Ayarlar", icon: Settings },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { meta } = useMeta();
  const productName = meta?.app_name ?? "Tehdit Modelleme Platformu";

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-surface md:flex">
      <div className="flex items-center gap-2.5 px-5 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <ShieldHalf className="h-4 w-4" aria-hidden />
        </span>
        <span className="text-sm font-semibold leading-tight">{productName}</span>
      </div>

      <nav aria-label="Ana gezinme" className="flex-1 space-y-1 px-3 py-2">
        {NAV.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
                active
                  ? "bg-accent-subtle font-medium text-accent"
                  : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" aria-hidden />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border px-5 py-3 text-xs text-muted-foreground">
        <p className="flex items-center gap-1.5">
          <FileSearch className="h-3.5 w-3.5" aria-hidden />
          Sürüm {meta?.version ?? "—"}
        </p>
        <p className="mt-1">Örnek Banka A.Ş. · Demo</p>
      </div>
    </aside>
  );
}
