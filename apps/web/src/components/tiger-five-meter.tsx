import type { RoundAnalytics } from "@/lib/api";
import { StatTile } from "@/components/stat-tile";
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
    <section aria-labelledby="tiger-five-heading" className="rounded-xl border p-4">
      <h2 id="tiger-five-heading" className="text-lg font-semibold">
        Tiger 5 Disaster Meter
      </h2>

      <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
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

      <div className="mt-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Clean Card Index</span>
          <span className="font-semibold">{cci}%</span>
        </div>
        <div
          role="meter"
          aria-valuenow={cci}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Clean Card Index"
          className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted"
        >
          <div
            className={cn("h-full rounded-full", METER_FILL_CLASSES[tone])}
            style={{ width: `${cci}%` }}
          />
        </div>
      </div>
    </section>
  );
}
