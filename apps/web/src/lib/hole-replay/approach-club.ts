import type { HoleReplayShot } from "@/lib/api";

/** The shot most relevant to "did this land in my usual dispersion
 * pattern" for a hole — the shot that reached the green (or its fringe),
 * since that's the shot the Dispersion Cone Visualizer (PRD §5.3) is meant
 * to contextualize. `null` if no shot on this hole reached the green (e.g.
 * a hole that isn't finished yet). */
export function pickApproachShot(shots: HoleReplayShot[]): HoleReplayShot | null {
  return shots.find((shot) => shot.end_lie === "green" || shot.end_lie === "fringe") ?? null;
}

/** `null` if there's no approach shot, or it has no club recorded. */
export function pickApproachClub(shots: HoleReplayShot[]): string | null {
  return pickApproachShot(shots)?.club ?? null;
}
