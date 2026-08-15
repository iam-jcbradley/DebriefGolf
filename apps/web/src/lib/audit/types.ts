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
// hole *number* (1-18) rather than a `hole_id` FK: the wizard operates on a
// freshly-uploaded round that may not have a course/holes assigned yet
// (POST /api/rounds/upload creates a course-less Round — see
// app/models/round.py). Submitting a draft to the backend needs a course
// assigned first, which needs a course-matching or manual course-picker
// flow this phase doesn't build (see docs/DEVELOPMENT_PLAN.md Phase 3).
export interface DraftShot {
  id: string;
  holeNumber: number;
  shotNumber: number;
  club: string | null;
  startLie: Lie;
  endLie: Lie;
  startDistanceYards: number;
  endDistanceYards: number;
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
