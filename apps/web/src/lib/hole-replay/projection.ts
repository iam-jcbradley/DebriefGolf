// Mirrors apps/api/app/services/geometry.py's flat-earth approximation
// exactly (same constant, same math) so the SVG schematic's shot placement
// agrees with the backend's own lateral-dispersion numbers. Golf holes are
// small enough (a few hundred yards) that this is accurate to a fraction of
// an inch — nowhere near enough curvature to matter.
const YARDS_PER_DEGREE_LAT = 121_000.0;

export interface LatLng {
  lat: number;
  lng: number;
}

export function localYards(origin: LatLng, point: LatLng): { east: number; north: number } {
  const north = (point.lat - origin.lat) * YARDS_PER_DEGREE_LAT;
  const east =
    (point.lng - origin.lng) * YARDS_PER_DEGREE_LAT * Math.cos((origin.lat * Math.PI) / 180);
  return { east, north };
}

export interface AimLineOffset {
  longitudinalYards: number;
  lateralYards: number;
}

/** Decomposes `point` into components along and across the tee->green aim
 * line. Positive lateral = right of the tee->green direction. */
export function offsetFromAimLine(tee: LatLng, green: LatLng, point: LatLng): AimLineOffset {
  const aim = localYards(tee, green);
  const aimLength = Math.hypot(aim.east, aim.north);
  if (aimLength === 0) {
    throw new Error("tee and green coincide — no aim line to project onto");
  }

  const aimUnit = { x: aim.east / aimLength, y: aim.north / aimLength };
  const perpUnit = { x: aimUnit.y, y: -aimUnit.x }; // 90° clockwise from aim direction

  const p = localYards(tee, point);
  const longitudinalYards = p.east * aimUnit.x + p.north * aimUnit.y;
  const lateralYards = p.east * perpUnit.x + p.north * perpUnit.y;

  return { longitudinalYards, lateralYards };
}

export function localYardsToLatLng(origin: LatLng, east: number, north: number): LatLng {
  return {
    lat: origin.lat + north / YARDS_PER_DEGREE_LAT,
    lng: origin.lng + east / (YARDS_PER_DEGREE_LAT * Math.cos((origin.lat * Math.PI) / 180)),
  };
}

/** Inverse of `offsetFromAimLine`: recovers the absolute lat/lng for a
 * longitudinal/lateral offset from the tee->green aim line. Used when a
 * user clicks a point on the hole map (course builder, manual shot entry)
 * and that click needs to become a real GPS point to submit to the
 * backend. */
export function offsetToLatLng(tee: LatLng, green: LatLng, offset: AimLineOffset): LatLng {
  const aim = localYards(tee, green);
  const aimLength = Math.hypot(aim.east, aim.north);
  if (aimLength === 0) {
    throw new Error("tee and green coincide — no aim line to project onto");
  }

  const aimUnit = { x: aim.east / aimLength, y: aim.north / aimLength };
  const perpUnit = { x: aimUnit.y, y: -aimUnit.x };

  const east = offset.longitudinalYards * aimUnit.x + offset.lateralYards * perpUnit.x;
  const north = offset.longitudinalYards * aimUnit.y + offset.lateralYards * perpUnit.y;

  return localYardsToLatLng(tee, east, north);
}
