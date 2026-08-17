import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";
import { StatTile, type StatTileTone } from "@/components/stat-tile";
import type { RoundAnalytics, RoundSummary, SGCategory } from "@/lib/api";

// No "SG: " prefix — the card is titled Strokes Gained and these four sit
// in one grid, so repeating it on every tile just costs caption width and
// wraps the longer labels onto a second line.
const CATEGORY_LABELS: Record<SGCategory, string> = {
  OTT: "Off the Tee",
  APP: "Approach",
  ARG: "Around the Green",
  PUTT: "Putting",
};

const CATEGORY_ORDER: SGCategory[] = ["OTT", "APP", "ARG", "PUTT"];

function formatSigned(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function formatToPar(score: number, par: number): string {
  const diff = score - par;
  if (diff === 0) return "E";
  return diff > 0 ? `+${diff}` : `${diff}`;
}

function toneFor(value: number): StatTileTone {
  if (value > 0.05) return "good";
  if (value < -0.05) return "bad";
  return "neutral";
}

export interface RoundSnapshotProps {
  round: RoundSummary;
  analytics: RoundAnalytics;
  /** Course this round was played at. Optional so the component still
   * renders for a round with no course attached. */
  courseName?: string;
  /** Sum of par across the round's holes, for the score-to-par figure. */
  coursePar?: number | null;
}

const TONE_TEXT_CLASSES: Record<StatTileTone, string> = {
  good: "text-delta-good-text",
  bad: "text-delta-bad-text",
  neutral: "text-foreground",
};

export function RoundSnapshot({ round, analytics, courseName, coursePar }: RoundSnapshotProps) {
  const totalTone = toneFor(analytics.strokes_gained.total);
  const playedAt = new Date(round.played_at).toLocaleDateString(undefined, {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <Card aria-labelledby="round-snapshot-heading">
      <CardHeader>
        <Overline>{playedAt}</Overline>
        <CardTitle id="round-snapshot-heading">{courseName ?? "Round Snapshot"}</CardTitle>
      </CardHeader>

      <CardContent>
        {/* The score is the anchor every other number on this page is read
            against (PRD §8), so it gets the serif numeral — not muted body
            text, which is where it used to sit. */}
        <div className="flex items-baseline gap-3 border-b border-border pb-5">
          <p className="stat-numeral">{round.total_score ?? "—"}</p>
          {round.total_score !== null && coursePar != null && (
            <p className="font-serif text-2xl font-medium text-muted-foreground tabular-nums">
              {formatToPar(round.total_score, coursePar)}
            </p>
          )}
          <p className="ml-auto text-sm text-muted-foreground">
            vs {analytics.handicap_bucket} handicap
          </p>
        </div>

        <Overline className="mt-5 mb-3">Strokes Gained</Overline>
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

        <div className="mt-5 flex items-baseline justify-between border-t border-border pt-4">
          <Overline as="span">Total</Overline>
          <span className={`font-serif text-2xl font-medium tabular-nums ${TONE_TEXT_CLASSES[totalTone]}`}>
            {formatSigned(analytics.strokes_gained.total)}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
