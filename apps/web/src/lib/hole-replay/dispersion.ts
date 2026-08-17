import type { DispersionEllipse } from "@/lib/api";

// Mirrors apps/api/app/services/dispersion.py's is_within_ellipse exactly
// (same math), so a "sucker pin" check made in the browser
// (rounds/[id]/page.tsx — is today's pin inside my typical dispersion
// pattern for this club?) agrees with the backend's own ellipse math. The
// ellipse itself still comes from the backend (GET /bag); only the
// point-in-ellipse test is duplicated here.
export function isWithinEllipse(
  ellipse: DispersionEllipse,
  longitudinalYards: number,
  lateralYards: number
): boolean {
  const dx = longitudinalYards - ellipse.center_longitudinal_yards;
  const dy = lateralYards - ellipse.center_lateral_yards;

  if (ellipse.semi_major_yards === 0 || ellipse.semi_minor_yards === 0) {
    return dx === 0 && dy === 0;
  }

  const normalized = (dx / ellipse.semi_major_yards) ** 2 + (dy / ellipse.semi_minor_yards) ** 2;
  return normalized <= 1.0;
}
