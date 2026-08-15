import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";
import type { SimVsRealGapping } from "@/lib/api";

export interface SimVsRealTableProps {
  rows: SimVsRealGapping[];
}

function fmt(value: number | null): string {
  return value === null ? "—" : `${value}y`;
}

function fmtDelta(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value}y`;
}

/** Sim vs. Real-World Gapping Delta (PRD §6.1): compares R10/R50 range
 * carry averages against on-course GPS-tracked carry (Smart Bag) per club,
 * so a range session's numbers can be trusted (or discounted) on the
 * course. */
export function SimVsRealTable({ rows }: SimVsRealTableProps) {
  return (
    <Card>
      <CardHeader>
        <Overline>Range vs. course</Overline>
        <CardTitle className="text-lg">Sim vs. Real-World Gapping</CardTitle>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Needs both a launch monitor session and on-course rounds for at least one shared club.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="py-2 pr-3 font-normal">Club</th>
                  <th className="py-2 pr-3 font-normal">Range carry</th>
                  <th className="py-2 pr-3 font-normal">On-course carry</th>
                  <th className="py-2 font-normal">Delta</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.club} className="border-b border-border last:border-0">
                    <td className="py-2 pr-3 font-medium">{row.club}</td>
                    <td className="py-2 pr-3">{fmt(row.range_carry_mean_yards)}</td>
                    <td className="py-2 pr-3">{fmt(row.on_course_carry_mean_yards)}</td>
                    <td className="py-2">{fmtDelta(row.delta_yards)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
