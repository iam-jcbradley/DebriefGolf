// PRD §4.2 "Strike Quality & Contact Tagging": a one-tap tagging modal for
// shots yielding worse than -0.4 Strokes Gained.
export const STRIKE_QUALITY_SG_THRESHOLD = -0.4;

export const STRIKE_QUALITY_TAGS = [
  "Toe",
  "Heel",
  "Fat",
  "Thin",
  "Push",
  "Pull",
  "Skulled",
  "Chunked",
] as const;

export type StrikeQualityTag = (typeof STRIKE_QUALITY_TAGS)[number];

/** `strokesGained` is `undefined` when it hasn't been computed yet (e.g. the
 * shot hasn't been submitted for analysis) — that's not reason to tag it. */
export function needsStrikeQualityTag(strokesGained: number | undefined): boolean {
  return strokesGained !== undefined && strokesGained < STRIKE_QUALITY_SG_THRESHOLD;
}
