import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";
import { StatTile, type StatTileTone } from "@/components/stat-tile";
import type { RoundAnalytics, RoundSummary, SGCategory } from "@/lib/api";

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

const TONE_TEXT_CLASSES: Record<StatTileTone, string> = {
  good: "text-delta-good-text",
  bad: "text-delta-bad-text",
  neutral: "text-foreground",
};

export function RoundSnapshot({ round, analytics }: RoundSnapshotProps) {
  const totalTone = toneFor(analytics.strokes_gained.total);

  return (
    <Card aria-labelledby="round-snapshot-heading">
      <CardHeader>
        <Overline>Round Summary</Overline>
        <CardTitle id="round-snapshot-heading">Round Snapshot</CardTitle>
        <p className="text-sm text-muted-foreground">
          Score: {round.total_score ?? "—"} · Handicap bucket: {analytics.handicap_bucket}
        </p>
      </CardHeader>

      <CardContent>
        <dl className="grid grid-cols-2 gap-3">
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

        <p className="mt-5 border-t border-border pt-4 text-sm">
          Total Strokes Gained:{" "}
          <span className={`font-semibold ${TONE_TEXT_CLASSES[totalTone]}`}>
            {formatSigned(analytics.strokes_gained.total)}
          </span>
        </p>
      </CardContent>
    </Card>
  );
}
