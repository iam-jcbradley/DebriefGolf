import type { Lie } from "@/lib/audit/types";

// PRD §4.2 "Penalty Drop Logic Wizard": distinguishes a lateral hazard drop
// from an out-of-bounds/lost-ball stroke-and-distance penalty — the two
// have different rules for where the next shot starts.
export type PenaltyType = "lateral_hazard" | "ob_lost_ball";

export interface PenaltyDropContext {
  /** The lie the shot that caused the penalty was played from. */
  precedingShotStartLie: Lie;
  /** The distance-to-hole that shot was played from. */
  precedingShotStartDistanceYards: number;
  /** The distance-to-hole where the ball entered the hazard (that shot's end distance). */
  enteredHazardDistanceYards: number;
}

export interface PenaltyDropResult {
  penaltyType: PenaltyType;
  dropLie: Lie;
  dropDistanceYards: number;
  tag: string;
}

/**
 * Where does play resume after each penalty type?
 * - Lateral hazard (Rule 17): a one-stroke penalty, dropped near where the
 *   ball crossed the hazard margin — distance-to-hole is essentially
 *   unchanged from where it entered.
 * - OB / lost ball: stroke-and-distance — replay from the *original* spot
 *   the penalized shot was hit from.
 *
 * Matches the pattern already used in the demo seed data
 * (apps/api/app/db/seed.py holes 2 and 14).
 */
export function classifyPenaltyDrop(
  penaltyType: PenaltyType,
  context: PenaltyDropContext
): PenaltyDropResult {
  if (penaltyType === "lateral_hazard") {
    return {
      penaltyType,
      // Conservative default lie for a hazard-margin drop; the user can
      // correct it in the wizard if the actual drop was on short grass etc.
      dropLie: "rough",
      dropDistanceYards: context.enteredHazardDistanceYards,
      tag: "Penalty: Lateral Hazard Drop",
    };
  }

  return {
    penaltyType,
    dropLie: context.precedingShotStartLie,
    dropDistanceYards: context.precedingShotStartDistanceYards,
    tag: "Penalty: Stroke & Distance",
  };
}
