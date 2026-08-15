import type { LatLng } from "@/lib/hole-replay/projection";

// Mirrors app.models.shot.Lie (apps/api) — kept in sync by hand, there's no
// shared schema between the two apps.
export const LIES = [
  "tee",
  "fairway",
  "rough",
  "sand",
  "recovery",
  "green",
  "fringe",
  "penalty",
  "hole",
] as const;

export type Lie = (typeof LIES)[number];

// A shot as the audit wizard edits it — not the API's `Shot` shape. Uses a
// hole *number* (1-18) rather than a `hole_id` FK, resolved server-side by
// POST /rounds/{id}/shots/bulk (PRD §10 Phase 5) once the round has a
// course. Shared by two flows: the Phase 3 audit wizard (reviewing a
// freshly-uploaded, course-less round — no `location`) and Phase 5's manual
// entry (a round already has a course, so `location` can be set by
// clicking the hole map — see components/manual-entry/hole-shot-entry.tsx).
export interface DraftShot {
  id: string;
  holeNumber: number;
  shotNumber: number;
  club: string | null;
  startLie: Lie;
  endLie: Lie;
  startDistanceYards: number;
  endDistanceYards: number;
  location?: LatLng | null;
  tag?: string;
  strokesGained?: number;

  // Audit wizard review state — undefined means "not yet reviewed for that
  // concern". Kept as separate flags (rather than overloading `tag`) since a
  // single shot can independently need more than one kind of review (e.g. a
  // shot that both entered a hazard and separately has bad strokes gained).
  penaltyReviewed?: boolean;
  fringeIsolationReviewed?: boolean;
  puttRoutingReviewed?: boolean;
  puttRouteResult?: { made: boolean } | { lagProximityFeet: number };
  strikeQualityReviewed?: boolean;
}
