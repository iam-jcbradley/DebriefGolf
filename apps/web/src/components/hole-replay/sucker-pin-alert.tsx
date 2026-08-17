// PRD §5.3 "sucker pin" strategy alert, the other half of ShortSidedBanner:
// this one fires *before* the shot, not after — today's pin sits inside the
// approach club's typical dispersion pattern (app/services/dispersion.py's
// is_within_ellipse, mirrored client-side in lib/hole-replay/dispersion.ts),
// a high-risk aim point rather than a missed one. `--status-warning`, not
// the short-sided banner's `--status-critical`: this is a heads-up about a
// risky pin position, not a report of a bad outcome.
export interface SuckerPinAlertProps {
  club: string;
}

export function SuckerPinAlert({ club }: SuckerPinAlertProps) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-status-warning/30 bg-status-warning/10 p-3 text-sm"
    >
      <p className="font-medium text-status-warning">⚠ Sucker pin</p>
      <p className="mt-1 text-muted-foreground">
        Today&apos;s pin sits inside your typical {club} dispersion pattern — a tucked, high-risk
        aim point.
      </p>
    </div>
  );
}
