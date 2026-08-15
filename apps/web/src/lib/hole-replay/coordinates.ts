import type { AimLineOffset } from "@/lib/hole-replay/projection";

export interface ViewBox {
  width: number;
  height: number;
  /** Extra room (yards) beyond the tee and beyond the green, so markers
   * near either end aren't clipped at the SVG edge. */
  paddingYards: number;
}

export interface SvgPoint {
  x: number;
  y: number;
}

/** Maps an aim-line offset to an SVG point: tee at the bottom, green at the
 * top (the conventional "looking up the fairway" hole-map orientation),
 * lateral offset increasing rightward — matching the backend's "positive =
 * right of the aim line" convention. Uses one uniform scale for both axes
 * so the shape isn't distorted. */
export function yardsToSvgPoint(
  offset: AimLineOffset,
  holeYardage: number,
  viewBox: ViewBox
): SvgPoint {
  const totalYards = holeYardage + viewBox.paddingYards * 2;
  const scale = viewBox.height / totalYards;
  return {
    x: viewBox.width / 2 + offset.lateralYards * scale,
    y: viewBox.height - (offset.longitudinalYards + viewBox.paddingYards) * scale,
  };
}

export function yardsToSvgLength(yards: number, holeYardage: number, viewBox: ViewBox): number {
  const totalYards = holeYardage + viewBox.paddingYards * 2;
  return yards * (viewBox.height / totalYards);
}

/** Inverse of `yardsToSvgPoint`: recovers the aim-line offset for a point
 * clicked on the SVG schematic (course builder, manual shot entry without a
 * Mapbox token). Combine with `offsetToLatLng` to get a real GPS point. */
export function svgPointToOffset(
  point: SvgPoint,
  holeYardage: number,
  viewBox: ViewBox
): AimLineOffset {
  const totalYards = holeYardage + viewBox.paddingYards * 2;
  const scale = viewBox.height / totalYards;
  return {
    lateralYards: (point.x - viewBox.width / 2) / scale,
    longitudinalYards: (viewBox.height - point.y) / scale - viewBox.paddingYards,
  };
}
