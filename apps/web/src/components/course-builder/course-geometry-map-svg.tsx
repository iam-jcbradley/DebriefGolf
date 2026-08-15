"use client";

import type { MouseEvent } from "react";
import { latLngToLocalPoint, localPointToLatLng, type LocalMapView } from "@/lib/course-builder/local-map";
import type { LatLng } from "@/lib/hole-replay/projection";

export interface CourseGeometryMapSvgProps {
  center: LatLng;
  tee: LatLng | null;
  green: LatLng | null;
  boundary: LatLng[];
  onPick: (latlng: LatLng) => void;
  width?: number;
  height?: number;
  /** How many yards one pixel represents — controls zoom level. */
  yardsPerPixel?: number;
}

const DEFAULT_WIDTH = 400;
const DEFAULT_HEIGHT = 400;
const DEFAULT_YARDS_PER_PIXEL = 1.5;

/**
 * Schematic fallback for `CourseGeometryMap` — always works, no Mapbox
 * token needed, and (in this sandbox) the only path that can actually be
 * manually verified, since outbound requests to Mapbox are blocked here.
 * Unlike `hole-replay/HoleReplaySvg`, there's no tee->green aim line to
 * orient against yet (that's what's being built), so this uses the
 * simpler, arbitrary-center `local-map` projection instead.
 */
export function CourseGeometryMapSvg({
  center,
  tee,
  green,
  boundary,
  onPick,
  width = DEFAULT_WIDTH,
  height = DEFAULT_HEIGHT,
  yardsPerPixel = DEFAULT_YARDS_PER_PIXEL,
}: CourseGeometryMapSvgProps) {
  const view: LocalMapView = { width, height, yardsPerPixel };

  function handleClick(event: MouseEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const point = {
      x: ((event.clientX - rect.left) / rect.width) * width,
      y: ((event.clientY - rect.top) / rect.height) * height,
    };
    onPick(localPointToLatLng(center, point, view));
  }

  const teePoint = tee ? latLngToLocalPoint(center, tee, view) : null;
  const greenPoint = green ? latLngToLocalPoint(center, green, view) : null;
  const boundaryPoints = boundary.map((p) => latLngToLocalPoint(center, p, view));

  return (
    <svg
      role="img"
      aria-label="Course geometry map — click to place a point"
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      onClick={handleClick}
      className="cursor-crosshair rounded-lg border bg-muted/30"
    >
      {teePoint && greenPoint && (
        <line
          x1={teePoint.x}
          y1={teePoint.y}
          x2={greenPoint.x}
          y2={greenPoint.y}
          stroke="var(--muted-foreground)"
          strokeDasharray="4 4"
        />
      )}
      {boundaryPoints.length >= 3 && (
        <polygon
          data-testid="green-boundary-polygon"
          points={boundaryPoints.map((p) => `${p.x},${p.y}`).join(" ")}
          fill="var(--status-positive, #2a9d5c)"
          fillOpacity={0.25}
          stroke="var(--status-positive, #2a9d5c)"
        />
      )}
      {boundaryPoints.map((p, i) => (
        <circle key={i} data-testid="boundary-point" cx={p.x} cy={p.y} r={3} fill="#d08a00" />
      ))}
      {teePoint && <circle data-testid="tee-point" cx={teePoint.x} cy={teePoint.y} r={6} fill="#0b0b0b" />}
      {greenPoint && (
        <circle data-testid="green-point" cx={greenPoint.x} cy={greenPoint.y} r={6} fill="#2a9d5c" />
      )}
    </svg>
  );
}
