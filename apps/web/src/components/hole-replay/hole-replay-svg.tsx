import type { MouseEvent } from "react";
import { DispersionEllipseOverlay } from "@/components/hole-replay/dispersion-ellipse-overlay";
import type { DispersionEllipse, HoleReplay, LatLngPoint } from "@/lib/api";
import {
  type ViewBox,
  svgPointToOffset,
  yardsToSvgLength,
  yardsToSvgPoint,
} from "@/lib/hole-replay/coordinates";
import { offsetFromAimLine, offsetToLatLng } from "@/lib/hole-replay/projection";

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
  width?: number;
  height?: number;
}

export function HoleReplaySvg({
  hole,
  ellipse,
  ellipseAnchorYards,
  onPick,
  width = 320,
  height = 480,
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

  const viewBox: ViewBox = { width, height, paddingYards: Math.max(20, hole.yardage * 0.08) };

  function project(point: LatLngPoint) {
    return yardsToSvgPoint(offsetFromAimLine(tee, green, point), hole.yardage, viewBox);
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
      width={width}
      height={height}
      role="img"
      aria-label={`Hole ${hole.hole_number} replay`}
      onClick={onPick ? handleClick : undefined}
      className={onPick ? "cursor-crosshair" : undefined}
    >
      <line
        x1={teePoint.x} y1={teePoint.y} x2={greenPoint.x} y2={greenPoint.y}
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
          radiusX={yardsToSvgLength(ellipse.semi_minor_yards, hole.yardage, viewBox)}
          radiusY={yardsToSvgLength(ellipse.semi_major_yards, hole.yardage, viewBox)}
        />
      )}

      <polyline
        points={[teePoint, ...shotPoints.map((s) => s.point)].map((p) => `${p.x},${p.y}`).join(" ")}
        fill="none" stroke="var(--primary)" strokeWidth={2}
      />

      <circle cx={teePoint.x} cy={teePoint.y} r={4} fill="var(--foreground)" />
      <circle cx={greenPoint.x} cy={greenPoint.y} r={4} fill="var(--status-good)" />

      {shotPoints.map(({ shot, point }) => (
        <circle
          key={shot.shot_id}
          cx={point.x} cy={point.y} r={5}
          fill={shot.approach_leave === "short_sided" ? "var(--status-critical)" : "var(--primary)"}
          stroke="var(--background)" strokeWidth={2}
        >
          <title>{`Shot ${shot.shot_number}${shot.club ? ` (${shot.club})` : ""}`}</title>
        </circle>
      ))}
    </svg>
  );
}
