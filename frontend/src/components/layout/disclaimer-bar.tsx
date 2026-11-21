import { TriangleAlert } from "lucide-react";

/**
 * Permanent, plain warning required on every screen: results are
 * possibilities derived from a document, not verified vulnerabilities.
 */
export function DisclaimerBar() {
  return (
    <div className="flex items-start gap-2 border-b border-level-high/30 bg-level-high/10 px-5 py-2 text-xs text-foreground">
      <TriangleAlert
        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-level-high"
        aria-hidden
      />
      <p>
        Bu tehditler dokümandan türetilen <strong>olasılıklardır</strong>; sistem
        testi yapılmadan kesin kabul edilmemelidir.
      </p>
    </div>
  );
}
