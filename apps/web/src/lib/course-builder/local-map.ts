import { localYards, localYardsToLatLng, type LatLng } from "@/lib/hole-replay/projection";

/**
 * A simple north-up local map, centered on an arbitrary point — for the
 * course builder's SVG fallback, which (unlike the hole-replay SVG) has no
 * tee->green aim line to orient against yet when a hole's geometry hasn't
 * been placed. Deliberately separate from `hole-replay/coordinates.ts`:
 * that module's `holeYardage` + aim-line framing is specific to viewing one
 * already-geometried hole, not an arbitrary area around a course.
 */
export interface LocalMapView {
  width: number;
  height: number;
  /** How many yards one pixel represents — controls zoom level. */
  yardsPerPixel: number;
}

export interface SvgPoint {
  x: number;
  y: number;
}

/** Maps a lat/lng to an SVG point: `center` at the middle of the view,
 * north up, east right. */
export function latLngToLocalPoint(center: LatLng, point: LatLng, view: LocalMapView): SvgPoint {
  const { east, north } = localYards(center, point);
  return {
    x: view.width / 2 + east / view.yardsPerPixel,
    y: view.height / 2 - north / view.yardsPerPixel,
  };
}

/** Inverse of `latLngToLocalPoint` — recovers the lat/lng a click landed
 * on. */
export function localPointToLatLng(center: LatLng, point: SvgPoint, view: LocalMapView): LatLng {
  const east = (point.x - view.width / 2) * view.yardsPerPixel;
  const north = (view.height / 2 - point.y) * view.yardsPerPixel;
  return localYardsToLatLng(center, east, north);
}
