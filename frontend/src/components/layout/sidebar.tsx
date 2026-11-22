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

// Each item says what the screen is for; a one-word label alone leaves
// people guessing where they are.
const NAV = [
  {
    href: "/",
    label: "Projeler",
    hint: "Yapılmış analizler",
    icon: ListChecks,
  },
  {
    href: "/analiz/yeni",
    label: "Yeni analiz",
    hint: "Doküman yükle veya örnek seç",
    icon: PlusCircle,
  },
  {
    href: "/pano",
    label: "Özet panosu",
    hint: "Risk dağılımı ve en kritik bulgular",
    icon: LayoutDashboard,
  },
  {
    href: "/bilgi-tabani",
    label: "Bilgi tabanı",
    hint: "Kaynaklar ve canlı arama",
    icon: BookOpen,
  },
  {
    href: "/denetim",
    label: "Denetim izi",
    hint: "Kim neyi değiştirdi",
    icon: ScrollText,
  },
  {
    href: "/ayarlar",
    label: "Ayarlar",
    hint: "LLM, eşikler, roller",
    icon: Settings,
  },
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
              title={item.hint}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-2 transition-colors",
                active
                  ? "bg-accent-subtle text-accent"
                  : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" aria-hidden />
              <span className={cn("text-sm", active && "font-medium")}>
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border px-5 py-2.5 text-[11px] text-muted-foreground">
        <p className="flex items-center gap-1.5">
          <FileSearch className="h-3 w-3" aria-hidden />
          Örnek Banka A.Ş. · demo · {meta?.version ?? "—"}
        </p>
      </div>
    </aside>
  );
}
