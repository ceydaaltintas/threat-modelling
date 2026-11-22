import { TriangleAlert } from "lucide-react";

/**
 * Permanent, plain warning required on every screen: results are
 * possibilities derived from a document, not verified vulnerabilities.
 */
export function DisclaimerBar() {
  return (
    <div className="flex items-center gap-1.5 border-b border-border bg-surface-muted px-5 py-1 text-[11px] text-muted-foreground">
      <TriangleAlert className="h-3 w-3 shrink-0 text-level-high" aria-hidden />
      <p>
        Bulgular dokümandan türetilen <strong>olasılıklardır</strong>; sistem
        testi yerine geçmez.
      </p>
    </div>
  );
}
