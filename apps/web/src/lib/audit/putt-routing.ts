import type { Lie } from "@/lib/audit/types";

// Matches apps/api/app/services/putting.py's thresholds exactly, so the
// wizard routes a putt the same way the backend's SG engine will later
// categorize it.
export const SHORT_PUTT_THRESHOLD_YARDS = 6 / 3; // 6ft
export const LONG_PUTT_THRESHOLD_YARDS = 20 / 3; // 20ft

export type PuttRoute = "short_putt" | "mid_putt" | "long_putt";

/**
 * PRD §5.2 putting mechanics split: short putts (<6ft) get a start-line
 * conversion prompt, long putts (>20ft) get a lag-proximity prompt.
 * Everything in between doesn't need either.
 */
export function routePutt(startDistanceYards: number): PuttRoute {
  if (startDistanceYards < SHORT_PUTT_THRESHOLD_YARDS) return "short_putt";
  if (startDistanceYards > LONG_PUTT_THRESHOLD_YARDS) return "long_putt";
  return "mid_putt";
}

/**
 * PRD §4.2 "Fringe vs. True Putting Isolation": prompts when a putter is
 * used from off the green. The wizard doesn't have a live green-boundary
 * containment check wired in (that needs the PostGIS query this component
 * has no access to) — using the putter club as the signal is a reasonable
 * proxy: any putt not already recorded as `green` is exactly the case PRD
 * §4.2 describes.
 */
export function needsFringeIsolationPrompt(club: string | null, startLie: Lie): boolean {
  return club === "Putter" && startLie !== "green";
}

export type FringeIsolationChoice = "true_putt" | "fringe_short_game";

/** Resolves the isolation prompt into the lie the shot should be recorded with. */
export function resolveFringeIsolation(choice: FringeIsolationChoice, currentLie: Lie): Lie {
  return choice === "true_putt" ? "green" : currentLie;
}
