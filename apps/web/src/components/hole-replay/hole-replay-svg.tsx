import type { MouseEvent } from "react";
import { DispersionEllipseOverlay } from "@/components/hole-replay/dispersion-ellipse-overlay";
import type { DispersionEllipse, HoleReplay, LatLngPoint } from "@/lib/api";
import {
  type ViewBox,
  svgPointToOffset,
  yardsToSvgLength,
  yardsToSvgLengthLateral,
  yardsToSvgPoint,
} from "@/lib/hole-replay/coordinates";
import { offsetFromAimLine, offsetToLatLng } from "@/lib/hole-replay/projection";

/** Never zoom the lateral axis tighter than this, or a dead-straight hole
 * (every shot on the aim line) would blow a two-yard wobble up to the full
 * width of the canvas and read as a wild slice. */
const MIN_LATERAL_HALF_YARDS = 18;

export interface HoleReplaySvgProps {
  hole: HoleReplay;
  /** A club's dispersion ellipse (e.g. from GET /api/bag/{userId}) — the
   * "where does this club typically land" overlay PRD §5.3 calls the
   * Dispersion Cone Visualizer. Its mean/stdev are *relative to where the
   * shot was struck from* (carry distance, not a hole position), so it
   * must be anchored to that spot via `ellipseAnchorYards` — omitting the
   * anchor while passing an ellipse would place it at the tee, which is
   * wrong for anything but a full tee shot. */
  ellipse?: DispersionEllipse | null;
  ellipseAnchorYards?: { longitudinal: number; lateral: number } | null;
  /** When set, clicking the map reports the clicked GPS point here instead
   * of the map being purely read-only (PRD §10 Phase 5 manual shot entry —
   * see components/manual-entry/hole-shot-entry.tsx). */
  onPick?: (latlng: LatLngPoint) => void;
  /** Shot number to emphasize — driven by hovering the shot list beside the
   * canvas, so the two halves of the replay view read as one thing. */
  highlightedShotNumber?: number | null;
  width?: number;
  height?: number;
  /** Fit the lateral axis to the shots actually played rather than sharing
   * the longitudinal scale. On by default for the read-only replay; the
   * click-to-place surfaces pass `false`, because there the whole point is
   * that where you click is where the ball was. */
  fitLateral?: boolean;
}

export function HoleReplaySvg({
  hole,
  ellipse,
  ellipseAnchorYards,
  onPick,
  highlightedShotNumber = null,
  width = 320,
  height = 480,
  fitLateral = !onPick,
}: HoleReplaySvgProps) {
  if (!hole.tee || !hole.green_center) {
    return (
      <p className="text-sm text-muted-foreground">
        This hole doesn&apos;t have tee/green geometry recorded yet.
      </p>
    );
  }
  const tee = hole.tee;
  const green = hole.green_center;
  const paddingYards = Math.max(20, hole.yardage * 0.08);

  // Fitting needs offsets before there's a view box to project into, so
  // measure in yards first, then build the box around the result.
  const offsetOf = (point: LatLngPoint) => offsetFromAimLine(tee, green, point);
  const lateralExtents = [
    ...hole.shots.filter((s) => s.location !== null).map((s) => offsetOf(s.location as LatLngPoint)),
    ...(hole.pin ? [offsetOf(hole.pin)] : []),
    ...(hole.green_boundary ?? []).map(offsetOf),
  ].map((o) => Math.abs(o.lateralYards));

  const ellipseLateralReach = ellipse
    ? Math.abs((ellipseAnchorYards?.lateral ?? 0) + ellipse.center_lateral_yards) +
      ellipse.semi_minor_yards
    : 0;

  const lateralHalfYards = fitLateral
    ? Math.max(MIN_LATERAL_HALF_YARDS, ellipseLateralReach, ...lateralExtents) * 1.25
    : undefined;

  const viewBox: ViewBox = { width, height, paddingYards, lateralHalfYards };

  function project(point: LatLngPoint) {
    return yardsToSvgPoint(offsetOf(point), hole.yardage, viewBox);
  }

  function handleClick(event: MouseEvent<SVGSVGElement>) {
    if (!onPick) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const point = {
      x: ((event.clientX - rect.left) / rect.width) * width,
      y: ((event.clientY - rect.top) / rect.height) * height,
    };
    onPick(offsetToLatLng(tee, green, svgPointToOffset(point, hole.yardage, viewBox)));
  }

  const teePoint = project(tee);
  const greenPoint = project(green);
  const pinPoint = hole.pin ? project(hole.pin) : null;
  // The aim line and short-game reasoning both target the actual pin once
  // one's been recorded (Phase 14) — the green center is a fallback, not
  // the goal, once real data exists.
  const aimPoint = pinPoint ?? greenPoint;
  const boundaryPoints = hole.green_boundary?.map(project);

  const shotsWithLocation = hole.shots.filter(
    (shot): shot is typeof shot & { location: LatLngPoint } => shot.location !== null
  );
  const shotPoints = shotsWithLocation.map((shot) => ({ shot, point: project(shot.location) }));

  const anchor = ellipseAnchorYards ?? { longitudinal: 0, lateral: 0 };
  const ellipseCenter = ellipse
    ? yardsToSvgPoint(
        {
          longitudinalYards: anchor.longitudinal + ellipse.center_longitudinal_yards,
          lateralYards: anchor.lateral + ellipse.center_lateral_yards,
        },
        hole.yardage,
        viewBox
      )
    : null;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={`Hole ${hole.hole_number} replay`}
      onClick={onPick ? handleClick : undefined}
      className={`h-auto w-full ${onPick ? "cursor-crosshair" : ""}`}
    >
      <line
        x1={teePoint.x} y1={teePoint.y} x2={aimPoint.x} y2={aimPoint.y}
        stroke="var(--border)" strokeDasharray="4 4"
      />

      {boundaryPoints && (
        <polygon
          points={boundaryPoints.map((p) => `${p.x},${p.y}`).join(" ")}
          fill="var(--status-good)" fillOpacity={0.15} stroke="var(--status-good)"
        />
      )}

      {ellipse && ellipseCenter && (
        <DispersionEllipseOverlay
          centerX={ellipseCenter.x}
          centerY={ellipseCenter.y}
          radiusX={yardsToSvgLengthLateral(ellipse.semi_minor_yards, hole.yardage, viewBox)}
          radiusY={yardsToSvgLength(ellipse.semi_major_yards, hole.yardage, viewBox)}
        />
      )}

      <polyline
        points={[teePoint, ...shotPoints.map((s) => s.point)].map((p) => `${p.x},${p.y}`).join(" ")}
        fill="none" stroke="var(--primary)" strokeWidth={2}
      />

      <circle cx={teePoint.x} cy={teePoint.y} r={4} fill="var(--foreground)" />
      <circle cx={greenPoint.x} cy={greenPoint.y} r={4} fill="var(--status-good)" />

      {pinPoint && (
        <g data-testid="pin-marker">
          <line
            x1={pinPoint.x} y1={pinPoint.y} x2={pinPoint.x} y2={pinPoint.y - 14}
            stroke="var(--foreground)" strokeWidth={1.5}
          />
          <path
            d={`M ${pinPoint.x} ${pinPoint.y - 14} L ${pinPoint.x + 9} ${pinPoint.y - 10.5} L ${pinPoint.x} ${pinPoint.y - 7} Z`}
            fill="var(--primary)"
          />
        </g>
      )}

      {shotPoints.map(({ shot, point }) => {
        const highlighted = highlightedShotNumber === shot.shot_number;
        return (
          <circle
            key={shot.shot_id}
            cx={point.x} cy={point.y} r={highlighted ? 8 : 5}
            fill={shot.approach_leave === "short_sided" ? "var(--status-critical)" : "var(--primary)"}
            stroke={highlighted ? "var(--foreground)" : "var(--background)"}
            strokeWidth={2}
          >
            <title>{`Shot ${shot.shot_number}${shot.club ? ` (${shot.club})` : ""}`}</title>
          </circle>
        );
      })}
    </svg>
  );
}
