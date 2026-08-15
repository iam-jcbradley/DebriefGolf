"use client";

import { useState } from "react";
import { CourseGeometryMap } from "@/components/course-builder/course-geometry-map";
import type { LatLng } from "@/lib/hole-replay/projection";
import { cn } from "@/lib/utils";

export type GeometryPlacementMode = "tee" | "green" | "boundary";

const MODES: GeometryPlacementMode[] = ["tee", "green", "boundary"];

export interface HoleGeometryValue {
  tee_location: LatLng | null;
  green_center: LatLng | null;
  green_boundary: LatLng[] | null;
}

export interface HoleGeometryEditorProps {
  center: LatLng;
  value: HoleGeometryValue;
  onChange: (value: HoleGeometryValue) => void;
}

/**
 * Wraps `CourseGeometryMap` with a placement-mode selector — the map itself
 * just reports "the user clicked here"; this decides whether that click
 * sets the tee, the green center, or appends a green-boundary vertex.
 */
export function HoleGeometryEditor({ center, value, onChange }: HoleGeometryEditorProps) {
  const [mode, setMode] = useState<GeometryPlacementMode>("tee");
  const boundary = value.green_boundary ?? [];

  function handlePick(latlng: LatLng) {
    if (mode === "tee") {
      onChange({ ...value, tee_location: latlng });
    } else if (mode === "green") {
      onChange({ ...value, green_center: latlng });
    } else {
      onChange({ ...value, green_boundary: [...boundary, latlng] });
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-1" role="radiogroup" aria-label="Placement mode">
        {MODES.map((m) => (
          <button
            key={m}
            type="button"
            role="radio"
            aria-checked={mode === m}
            onClick={() => setMode(m)}
            className={cn(
              "rounded-md border px-2.5 py-1 text-sm capitalize",
              mode === m ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted"
            )}
          >
            {m === "boundary" ? "Green boundary" : m}
          </button>
        ))}
        {boundary.length > 0 && (
          <button
            type="button"
            onClick={() => onChange({ ...value, green_boundary: [] })}
            className="rounded-md border px-2.5 py-1 text-sm text-destructive hover:bg-muted"
          >
            Clear boundary
          </button>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        Click the map to place the {mode === "boundary" ? "next green boundary point" : mode}.
      </p>
      <CourseGeometryMap
        center={center}
        tee={value.tee_location}
        green={value.green_center}
        boundary={boundary}
        onPick={handlePick}
      />
    </div>
  );
}
