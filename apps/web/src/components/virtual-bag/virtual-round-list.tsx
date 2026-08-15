import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";
import type { SimPlatform, VirtualRound } from "@/lib/api";

const PLATFORM_LABELS: Record<SimPlatform, string> = {
  home_tee_hero: "Home Tee Hero",
  e6: "E6",
  gspro: "GSPro",
  other: "Other",
};

export interface VirtualRoundListProps {
  rounds: VirtualRound[];
}

/** Simulator round log (PRD §6.2) — deliberately its own list, not mixed
 * into the real-world Rounds page, so it reads as segregated from handicap
 * at a glance. */
export function VirtualRoundList({ rounds }: VirtualRoundListProps) {
  return (
    <Card>
      <CardHeader>
        <Overline>Sim log</Overline>
        <CardTitle className="text-lg">Virtual Rounds</CardTitle>
      </CardHeader>
      <CardContent>
        {rounds.length === 0 ? (
          <p className="text-sm text-muted-foreground">No virtual rounds logged yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {rounds.map((round) => (
              <li key={round.id} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-medium">{round.course_name}</p>
                  <p className="text-muted-foreground">
                    {PLATFORM_LABELS[round.platform]} ·{" "}
                    {new Date(round.played_at).toLocaleDateString()} · {round.holes_played} holes
                  </p>
                </div>
                <p className="stat-numeral text-xl">{round.total_score ?? "—"}</p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
