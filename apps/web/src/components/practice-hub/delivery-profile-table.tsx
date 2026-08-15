import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";
import type { ClubDeliveryProfile } from "@/lib/api";

export interface DeliveryProfileTableProps {
  clubs: ClubDeliveryProfile[];
}

function fmt(value: number | null, unit: string): string {
  return value === null ? "—" : `${value}${unit}`;
}

/** Per-club R10/R50 delivery numbers (PRD §6.1): Club Path, Face Angle, the
 * derived Face-to-Path, Spin Axis, Smash Factor, and average carry. */
export function DeliveryProfileTable({ clubs }: DeliveryProfileTableProps) {
  return (
    <Card>
      <CardHeader>
        <Overline>R10 / R50</Overline>
        <CardTitle className="text-lg">Delivery Profile</CardTitle>
      </CardHeader>
      <CardContent>
        {clubs.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No launch monitor sessions on file yet — upload an R10/R50 export to see per-club
            delivery numbers.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="py-2 pr-3 font-normal">Club</th>
                  <th className="py-2 pr-3 font-normal">Shots</th>
                  <th className="py-2 pr-3 font-normal">Path</th>
                  <th className="py-2 pr-3 font-normal">Face</th>
                  <th className="py-2 pr-3 font-normal">Face-to-Path</th>
                  <th className="py-2 pr-3 font-normal">Spin Axis</th>
                  <th className="py-2 pr-3 font-normal">Smash</th>
                  <th className="py-2 font-normal">Avg Carry</th>
                </tr>
              </thead>
              <tbody>
                {clubs.map((club) => (
                  <tr key={club.club} className="border-b border-border last:border-0">
                    <td className="py-2 pr-3 font-medium">{club.club}</td>
                    <td className="py-2 pr-3">{club.shot_count}</td>
                    <td className="py-2 pr-3">{fmt(club.avg_club_path_deg, "°")}</td>
                    <td className="py-2 pr-3">{fmt(club.avg_face_angle_deg, "°")}</td>
                    <td className="py-2 pr-3">{fmt(club.avg_face_to_path_deg, "°")}</td>
                    <td className="py-2 pr-3">{fmt(club.avg_spin_axis_deg, "°")}</td>
                    <td className="py-2 pr-3">{club.avg_smash_factor ?? "—"}</td>
                    <td className="py-2">{fmt(club.avg_carry_yards, "y")}</td>
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
