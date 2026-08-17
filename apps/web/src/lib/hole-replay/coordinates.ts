import type { AimLineOffset } from "@/lib/hole-replay/projection";

export interface ViewBox {
  width: number;
  height: number;
  /** Extra room (yards) beyond the tee and beyond the green, so markers
   * near either end aren't clipped at the SVG edge. */
  paddingYards: number;
  /** Half-width, in yards, of the lateral band the view should span.
   *
   * Omit it and both axes share one scale — true-to-life, and what the
   * course builder wants. Set it and the x axis gets its own scale, fitted
   * so `±lateralHalfYards` exactly fills the width. A hole is ~400y long
   * and maybe ±30y wide where the shots actually are, so at a shared scale
   * the played corridor collapses into a hairline down the middle of a
   * mostly empty box. This is a diagram of a hole, not a survey of one. */
  lateralHalfYards?: number;
}

export interface SvgPoint {
  x: number;
  y: number;
}

/** Yards → SVG units along the hole (the y axis). */
function longitudinalScale(holeYardage: number, viewBox: ViewBox): number {
  return viewBox.height / (holeYardage + viewBox.paddingYards * 2);
}

/** Yards → SVG units across the hole (the x axis). Falls back to the
 * longitudinal scale when no lateral band is specified, which keeps the
 * transform uniform and undistorted. */
function lateralScale(holeYardage: number, viewBox: ViewBox): number {
  if (viewBox.lateralHalfYards === undefined || viewBox.lateralHalfYards <= 0) {
    return longitudinalScale(holeYardage, viewBox);
  }
  return viewBox.width / 2 / viewBox.lateralHalfYards;
}

/** Maps an aim-line offset to an SVG point: tee at the bottom, green at the
 * top (the conventional "looking up the fairway" hole-map orientation),
 * lateral offset increasing rightward — matching the backend's "positive =
 * right of the aim line" convention. */
export function yardsToSvgPoint(
  offset: AimLineOffset,
  holeYardage: number,
  viewBox: ViewBox
): SvgPoint {
  return {
    x: viewBox.width / 2 + offset.lateralYards * lateralScale(holeYardage, viewBox),
    y:
      viewBox.height -
      (offset.longitudinalYards + viewBox.paddingYards) * longitudinalScale(holeYardage, viewBox),
  };
}

/** Length along the hole (y axis) in SVG units. */
export function yardsToSvgLength(yards: number, holeYardage: number, viewBox: ViewBox): number {
  return yards * longitudinalScale(holeYardage, viewBox);
}

/** Length across the hole (x axis) in SVG units. Equal to `yardsToSvgLength`
 * unless the view box sets its own lateral band — an ellipse's semi-minor
 * radius has to use this one or it won't match the marker positions. */
export function yardsToSvgLengthLateral(
  yards: number,
  holeYardage: number,
  viewBox: ViewBox
): number {
  return yards * lateralScale(holeYardage, viewBox);
}

/** Inverse of `yardsToSvgPoint`: recovers the aim-line offset for a point
 * clicked on the SVG schematic (course builder, manual shot entry without a
 * Mapbox token). Combine with `offsetToLatLng` to get a real GPS point. */
export function svgPointToOffset(
  point: SvgPoint,
  holeYardage: number,
  viewBox: ViewBox
): AimLineOffset {
  return {
    lateralYards: (point.x - viewBox.width / 2) / lateralScale(holeYardage, viewBox),
    longitudinalYards:
      (viewBox.height - point.y) / longitudinalScale(holeYardage, viewBox) - viewBox.paddingYards,
  };
}
