// Phase 14: discloses when a hole's short-siding verdict used the
// distance/lie proxy instead of the real geometric rule — true for nearly
// every round at launch, so this is routine data provenance, not a
// warning. Deliberately outside ShortSidedBanner and its
// `--status-critical` styling (see docs/DEVELOPMENT_PLAN.md Phase 14):
// that color is reserved for an actual disaster flag.
export interface PinProvenanceNoteProps {
  hasPin: boolean;
  hasGreenBoundary: boolean;
}

export function PinProvenanceNote({ hasPin, hasGreenBoundary }: PinProvenanceNoteProps) {
  if (hasPin && hasGreenBoundary) return null;

  const message = !hasPin
    ? "Based on green center — no pin recorded"
    : "Based on distance — no green boundary recorded";

  return <p className="text-sm text-muted-foreground">{message}</p>;
}
