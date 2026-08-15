"use client";

import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import type { DeliveryTrendPoint } from "@/lib/api";

export interface DeliveryTrendChartProps {
  club: string;
  points: DeliveryTrendPoint[];
}

/** Smash factor across practice sessions for one club (PRD §6.1's "delivery
 * profile view ... trends over practice sessions"). Fixed pixel dimensions
 * rather than `ResponsiveContainer`, which depends on `ResizeObserver` —
 * not available in every render environment this project's tests run in. */
export function DeliveryTrendChart({ club, points }: DeliveryTrendChartProps) {
  if (points.length < 2) {
    return (
      <p className="text-sm text-muted-foreground">
        Need at least two {club} sessions on file to plot a trend.
      </p>
    );
  }

  const data = points.map((point) => ({
    date: new Date(point.recorded_at).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    }),
    smash: point.avg_smash_factor,
    carry: point.avg_carry_yards,
  }));

  return (
    <div className="overflow-x-auto" role="img" aria-label={`${club} smash factor trend`}>
      <LineChart width={480} height={220} data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
        <YAxis
          domain={["auto", "auto"]}
          tick={{ fontSize: 12 }}
          stroke="var(--color-muted-foreground)"
          width={40}
        />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="smash"
          name="Smash factor"
          stroke="var(--color-chart-1)"
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </LineChart>
    </div>
  );
}
