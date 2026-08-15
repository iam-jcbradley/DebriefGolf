import type { RoundAnalytics, RoundSummary, SGCategory } from "@/lib/api";
import { StatTile, type StatTileTone } from "@/components/stat-tile";

const CATEGORY_LABELS: Record<SGCategory, string> = {
  OTT: "SG: Off the Tee",
  APP: "SG: Approach",
  ARG: "SG: Around the Green",
  PUTT: "SG: Putting",
};

const CATEGORY_ORDER: SGCategory[] = ["OTT", "APP", "ARG", "PUTT"];

function formatSigned(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function toneFor(value: number): StatTileTone {
  if (value > 0.05) return "good";
  if (value < -0.05) return "bad";
  return "neutral";
}

export interface RoundSnapshotProps {
  round: RoundSummary;
  analytics: RoundAnalytics;
}

export function RoundSnapshot({ round, analytics }: RoundSnapshotProps) {
  const totalTone = toneFor(analytics.strokes_gained.total);

  return (
    <section aria-labelledby="round-snapshot-heading" className="rounded-xl border p-4">
      <h2 id="round-snapshot-heading" className="text-lg font-semibold">
        Round Snapshot
      </h2>
      <p className="text-sm text-muted-foreground">
        Score: {round.total_score ?? "—"} · Handicap bucket: {analytics.handicap_bucket}
      </p>

      <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {CATEGORY_ORDER.map((category) => {
          const value = analytics.strokes_gained.by_category[category];
          return (
            <StatTile
              key={category}
              label={CATEGORY_LABELS[category]}
              value={formatSigned(value)}
              tone={toneFor(value)}
            />
          );
        })}
      </dl>

      <p className="mt-4 text-sm">
        Total Strokes Gained:{" "}
        <span
          className={
            totalTone === "good"
              ? "font-semibold text-delta-good-text"
              : totalTone === "bad"
                ? "font-semibold text-delta-bad-text"
                : "font-semibold"
          }
        >
          {formatSigned(analytics.strokes_gained.total)}
        </span>
      </p>
    </section>
  );
}
