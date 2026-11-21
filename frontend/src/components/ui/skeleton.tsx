import { cn } from "@/lib/utils";

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("skeleton rounded-md", className)} {...props} />;
}

/** Table-shaped loading placeholder used on list screens. */
export function SkeletonRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2" aria-hidden>
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-11 w-full" />
      ))}
    </div>
  );
}
