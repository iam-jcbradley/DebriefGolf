import {
  classifyPenaltyDrop,
  type PenaltyDropResult,
  type PenaltyType,
} from "@/lib/audit/penalty-classifier";
import { needsStrikeQualityTag, type StrikeQualityTag } from "@/lib/audit/strike-quality";
import type { DraftShot, Lie } from "@/lib/audit/types";

export type AuditReviewItem =
  | { type: "penalty"; shotId: string }
  | { type: "fringe_isolation"; shotId: string }
  | { type: "putt_routing"; shotId: string }
  | { type: "strike_quality"; shotId: string };

function isConfirmedPutt(shot: DraftShot): boolean {
  // After fringe isolation resolves, resolveFringeIsolation() has already
  // rewritten startLie to "green" (true putt) or left it as-is (short
  // game) — so this single check reflects the outcome without a second flag.
  return shot.club === "Putter" && shot.startLie === "green";
}

/**
 * One review item per shot at a time, in priority order (penalty first,
 * then fringe isolation, then putt routing, then strike quality) — each
 * concern is only surfaced once the one before it (for that shot) is
 * resolved, so the wizard doesn't ask about putt speed on a shot whose lie
 * hasn't been confirmed yet.
 */
export function computeReviewQueue(shots: DraftShot[]): AuditReviewItem[] {
  const items: AuditReviewItem[] = [];

  for (const shot of shots) {
    if (shot.endLie === "penalty" && !shot.penaltyReviewed) {
      items.push({ type: "penalty", shotId: shot.id });
      continue;
    }
    if (shot.club === "Putter" && shot.startLie !== "green" && !shot.fringeIsolationReviewed) {
      items.push({ type: "fringe_isolation", shotId: shot.id });
      continue;
    }
    if (isConfirmedPutt(shot) && !shot.puttRoutingReviewed) {
      items.push({ type: "putt_routing", shotId: shot.id });
      continue;
    }
    if (needsStrikeQualityTag(shot.strokesGained) && !shot.strikeQualityReviewed) {
      items.push({ type: "strike_quality", shotId: shot.id });
    }
  }

  return items;
}

function findShotIndex(shots: DraftShot[], shotId: string): number {
  const index = shots.findIndex((shot) => shot.id === shotId);
  if (index === -1) throw new Error(`No draft shot with id ${shotId}`);
  return index;
}

/** Renumbers shotNumber sequentially within one hole, starting from 1. */
function renumberHole(shots: DraftShot[], holeNumber: number): DraftShot[] {
  let n = 0;
  return shots.map((shot) =>
    shot.holeNumber === holeNumber ? { ...shot, shotNumber: ++n } : shot
  );
}

/**
 * Marks the hazard-entry shot reviewed and inserts the penalty-stroke
 * marker row right after it (same convention as apps/api/app/db/seed.py:
 * a `penalty -> penalty` row at the drop distance, distinct from whatever
 * shot actually continues play from there — that continuation shot is
 * either already in the draft, or the user adds it separately; this
 * function only accounts for the stroke the penalty itself costs).
 */
export function applyPenaltyResolution(
  shots: DraftShot[],
  shotId: string,
  penaltyType: PenaltyType
): DraftShot[] {
  const index = findShotIndex(shots, shotId);
  const shot = shots[index];
  const result: PenaltyDropResult = classifyPenaltyDrop(penaltyType, {
    precedingShotStartLie: shot.startLie,
    precedingShotStartDistanceYards: shot.startDistanceYards,
    enteredHazardDistanceYards: shot.endDistanceYards,
  });

  const reviewedShot: DraftShot = { ...shot, penaltyReviewed: true };
  const markerShot: DraftShot = {
    id: `${shot.id}-penalty-marker`,
    holeNumber: shot.holeNumber,
    shotNumber: shot.shotNumber + 1,
    club: null,
    startLie: "penalty",
    endLie: "penalty",
    startDistanceYards: result.dropDistanceYards,
    endDistanceYards: result.dropDistanceYards,
    tag: result.tag,
    penaltyReviewed: true,
  };

  const next = [...shots];
  next.splice(index, 1, reviewedShot, markerShot);
  return renumberHole(next, shot.holeNumber);
}

export function applyFringeIsolationResolution(
  shots: DraftShot[],
  shotId: string,
  resolvedLie: Lie
): DraftShot[] {
  const index = findShotIndex(shots, shotId);
  const next = [...shots];
  next[index] = { ...next[index], startLie: resolvedLie, fringeIsolationReviewed: true };
  return next;
}

export function applyPuttRoutingResolution(
  shots: DraftShot[],
  shotId: string,
  result: { made: boolean } | { lagProximityFeet: number }
): DraftShot[] {
  const index = findShotIndex(shots, shotId);
  const shot = shots[index];
  const madeIt = "made" in result && result.made;

  const next = [...shots];
  next[index] = {
    ...shot,
    puttRoutingReviewed: true,
    puttRouteResult: result,
    endLie: madeIt ? "hole" : shot.endLie,
    endDistanceYards: madeIt ? 0 : shot.endDistanceYards,
  };
  return next;
}

export function applyStrikeQualityResolution(
  shots: DraftShot[],
  shotId: string,
  tag: StrikeQualityTag
): DraftShot[] {
  const index = findShotIndex(shots, shotId);
  const next = [...shots];
  next[index] = { ...next[index], tag, strikeQualityReviewed: true };
  return next;
}

/** Skips a review item without resolving it (e.g. the strike-quality modal's Skip). */
export function markReviewed(
  shots: DraftShot[],
  shotId: string,
  type: AuditReviewItem["type"]
): DraftShot[] {
  const index = findShotIndex(shots, shotId);
  const flag = {
    penalty: "penaltyReviewed",
    fringe_isolation: "fringeIsolationReviewed",
    putt_routing: "puttRoutingReviewed",
    strike_quality: "strikeQualityReviewed",
  }[type] as keyof DraftShot;

  const next = [...shots];
  next[index] = { ...next[index], [flag]: true };
  return next;
}
