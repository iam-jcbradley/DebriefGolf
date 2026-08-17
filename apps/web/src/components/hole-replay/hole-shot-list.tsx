import { Overline } from "@/components/ui/overline";
import type { HoleReplayShot } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface HoleShotListProps {
  shots: HoleReplayShot[];
  highlightedShotNumber: number | null;
  onHighlight: (shotNumber: number | null) => void;
}

function formatSigned(value: number): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
}

/**
 * The shot-detail pane PRD §8 puts beside the hole canvas — "Shot 2: 7-Iron
 * (162y) / Tag: Heel-Push / SG: -0.58". Hovering a row lifts its marker on
 * the canvas, which is the whole reason the two sit side by side: the
 * numbers and the picture have to be legible as one thing.
 */
export function HoleShotList({ shots, highlightedShotNumber, onHighlight }: HoleShotListProps) {
  if (shots.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No shots recorded for this hole yet.
      </p>
    );
  }

  return (
    <div>
      <Overline>Shots</Overline>
      <ul className="mt-3 divide-y divide-border border-t border-border">
        {shots.map((shot) => (
          <li
            key={shot.shot_id ?? shot.shot_number}
            onMouseEnter={() => onHighlight(shot.shot_number)}
            onMouseLeave={() => onHighlight(null)}
            className={cn(
              "flex items-baseline gap-3 py-2.5 text-sm transition-colors",
              highlightedShotNumber === shot.shot_number && "bg-muted/50"
            )}
          >
            <span className="w-4 shrink-0 text-muted-foreground tabular-nums">
              {shot.shot_number}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate">{shot.club ?? "—"}</span>
              <span className="block text-xs text-muted-foreground">
                {shot.start_distance_yards}y &rarr; {shot.end_distance_yards}y &middot;{" "}
                {shot.end_lie}
                {shot.approach_leave === "short_sided" && (
                  <span className="text-status-critical"> &middot; short-sided</span>
                )}
                {shot.tag && <span className="block">{shot.tag}</span>}
              </span>
            </span>
            {shot.strokes_gained !== null && (
              <span
                className={cn(
                  "shrink-0 font-serif text-base tabular-nums",
                  shot.strokes_gained > 0 ? "text-delta-good-text" : "text-delta-bad-text"
                )}
              >
                {formatSigned(shot.strokes_gained)}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
