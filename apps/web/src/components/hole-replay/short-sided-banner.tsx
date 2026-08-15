// PRD §5.3 "sucker pin" strategy alert: a short-sided miss (see
// app/services/approach.py's classify_approach_leave on the backend) means
// a tight up-and-down with little green to work with.
export interface ShortSidedBannerProps {
  holeNumber: number;
  shortSidedCount: number;
}

export function ShortSidedBanner({ holeNumber, shortSidedCount }: ShortSidedBannerProps) {
  if (shortSidedCount === 0) return null;

  return (
    <div
      role="alert"
      className="rounded-lg border border-status-critical/30 bg-status-critical/10 p-3 text-sm"
    >
      <p className="font-medium text-status-critical">
        ⚠ Short-sided miss on hole {holeNumber}
      </p>
      <p className="mt-1 text-muted-foreground">
        {shortSidedCount} approach shot{shortSidedCount === 1 ? "" : "s"} left a tight
        up-and-down — a &quot;sucker pin&quot; position with little green to work with.
      </p>
    </div>
  );
}
