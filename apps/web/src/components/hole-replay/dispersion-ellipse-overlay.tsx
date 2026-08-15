// PRD §5.3 "Dispersion Cone Visualizer". Pure SVG — takes center/radii
// already in the parent's coordinate space (pixels, or hole-relative
// yards if the parent <svg> sets its own viewBox) so it has no dependency
// on Mapbox or any particular map projection, and is trivially testable.
export interface DispersionEllipseOverlayProps {
  centerX: number;
  centerY: number;
  radiusX: number;
  radiusY: number;
  label?: string;
}

export function DispersionEllipseOverlay({
  centerX,
  centerY,
  radiusX,
  radiusY,
  label,
}: DispersionEllipseOverlayProps) {
  return (
    <g data-testid="dispersion-ellipse">
      <ellipse
        cx={centerX}
        cy={centerY}
        rx={radiusX}
        ry={radiusY}
        fill="var(--status-warning)"
        fillOpacity={0.15}
        stroke="var(--status-warning)"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
      {label && (
        <text
          x={centerX}
          y={centerY - radiusY - 4}
          textAnchor="middle"
          fontSize={10}
          fill="var(--muted-foreground)"
        >
          {label}
        </text>
      )}
    </g>
  );
}
