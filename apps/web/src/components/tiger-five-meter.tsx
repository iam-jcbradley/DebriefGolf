import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";
import { StatTile } from "@/components/stat-tile";
import type { RoundAnalytics } from "@/lib/api";
import { cn } from "@/lib/utils";

type TigerFive = RoundAnalytics["tiger_five"];

const VIOLATIONS: Array<{ key: keyof Omit<TigerFive, "clean_card_index">; label: string }> = [
  { key: "double_bogeys_or_worse", label: "Doubles+" },
  { key: "three_putts", label: "3-Putts" },
  { key: "par_five_bogeys", label: "Par 5 Bogeys" },
  { key: "blown_recoveries_inside_50", label: "Blown Recoveries" },
  { key: "penalties_inside_150", label: "Penalties Inside 150y" },
];

function meterTone(cci: number): "good" | "warning" | "critical" {
  if (cci >= 80) return "good";
  if (cci >= 50) return "warning";
  return "critical";
}

const METER_FILL_CLASSES = {
  good: "bg-status-good",
  warning: "bg-status-warning",
  critical: "bg-status-critical",
};

export interface TigerFiveMeterProps {
  tigerFive: TigerFive;
}

export function TigerFiveMeter({ tigerFive }: TigerFiveMeterProps) {
  const cci = tigerFive.clean_card_index;
  const tone = meterTone(cci);

  return (
    <Card aria-labelledby="tiger-five-heading">
      <CardHeader>
        <Overline>Where It Went Wrong</Overline>
        <CardTitle id="tiger-five-heading">Tiger 5 Disaster Meter</CardTitle>
      </CardHeader>

      <CardContent>
        {/* Three-up only once the card itself is genuinely wide. This card
            sits in the dashboard's `md:grid-cols-2`, so at 768–1024 a
            `sm:grid-cols-3` gave ~95px tiles and captions like "Blown
            Recoveries" overflowed their borders. */}
        <dl className="grid grid-cols-2 gap-3 xl:grid-cols-3">
          {VIOLATIONS.map(({ key, label }) => {
            const count = tigerFive[key];
            return (
              <StatTile
                key={key}
                label={label}
                value={String(count)}
                tone={count === 0 ? "good" : "bad"}
                indicator="status"
              />
            );
          })}
        </dl>

        <div className="mt-5 border-t border-border pt-4">
          <div className="flex items-center justify-between">
            <Overline>Clean Card Index</Overline>
            <span className="font-serif text-lg font-medium tabular-nums">{cci}%</span>
          </div>
          <div
            role="meter"
            aria-valuenow={cci}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Clean Card Index"
            className="mt-2 h-1.5 w-full overflow-hidden bg-muted"
          >
            <div
              className={cn("h-full", METER_FILL_CLASSES[tone])}
              style={{ width: `${cci}%` }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
