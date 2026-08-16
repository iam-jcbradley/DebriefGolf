"use client";

import "mapbox-gl/dist/mapbox-gl.css";
import { useEffect, useRef, useState } from "react";
import { HoleReplaySvg } from "@/components/hole-replay/hole-replay-svg";
import type { DispersionEllipse, HoleReplay, LatLngPoint } from "@/lib/api";

const ENV_MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

export interface HoleReplayMapProps {
  hole: HoleReplay;
  ellipse?: DispersionEllipse | null;
  /** Where to anchor `ellipse` — see `HoleReplaySvgProps.ellipseAnchorYards`. */
  ellipseAnchorYards?: { longitudinal: number; lateral: number } | null;
  /** When set, clicking the map reports the clicked GPS point here instead
   * of the map being purely read-only — see `HoleReplaySvgProps.onPick`. */
  onPick?: (latlng: LatLngPoint) => void;
  /** Shot to emphasize on the schematic — see `HoleReplaySvgProps`. Has no
   * effect on the satellite map, whose markers Mapbox owns. */
  highlightedShotNumber?: number | null;
  /** Overrides the NEXT_PUBLIC_MAPBOX_TOKEN env var — mainly for tests. */
  mapboxToken?: string;
}

/**
 * Satellite hole replay (PRD §5.3 "Mapbox GL integration rendering hole
 * satellite imagery with the plotted shot vector per hole"). Needs a real
 * Mapbox access token, which this environment doesn't have (no developer
 * account configured here) — same boundary as the Garmin OAuth plumbing.
 * Falls back to `HoleReplaySvg`'s schematic view (real geometry, same data,
 * no satellite imagery) whenever no token is configured or the map fails
 * to load, so the feature still works end to end without one.
 *
 * `mapbox-gl` is dynamically imported (only when a token is actually
 * configured) rather than statically, so the common no-token path doesn't
 * pull ~500KB of mapping library into this route's bundle for nothing.
 */
export function HoleReplayMap({
  hole,
  ellipse,
  ellipseAnchorYards,
  onPick,
  highlightedShotNumber = null,
  mapboxToken,
}: HoleReplayMapProps) {
  const token = mapboxToken ?? ENV_MAPBOX_TOKEN;
  const containerRef = useRef<HTMLDivElement>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  // Read inside the click handler without adding `onPick` to the mount
  // effect's deps — a new function identity on every parent render
  // shouldn't tear down and rebuild the live map.
  const onPickRef = useRef(onPick);
  onPickRef.current = onPick;

  useEffect(() => {
    if (!token || !hole.tee || !containerRef.current) return;

    let cancelled = false;
    let map: import("mapbox-gl").Map | undefined;

    import("mapbox-gl").then(({ default: mapboxgl }) => {
      if (cancelled || !containerRef.current) return;

      mapboxgl.accessToken = token;
      map = new mapboxgl.Map({
        container: containerRef.current,
        style: "mapbox://styles/mapbox/satellite-streets-v12",
        center: [hole.tee!.lng, hole.tee!.lat],
        zoom: 16,
      });

      map.on("error", (event) => setMapError(event.error?.message ?? "Failed to load the map"));
      map.on("click", (event) => {
        onPickRef.current?.({ lat: event.lngLat.lat, lng: event.lngLat.lng });
      });

      map.on("load", () => {
        if (!map) return;
        new mapboxgl.Marker({ color: "#0b0b0b" })
          .setLngLat([hole.tee!.lng, hole.tee!.lat])
          .addTo(map);
        if (hole.green_center) {
          new mapboxgl.Marker({ color: "#0ca30c" })
            .setLngLat([hole.green_center.lng, hole.green_center.lat])
            .addTo(map);
        }
        // The actual pin position (Phase 14) — distinct from the green
        // marker above, which stays put regardless of where the hole was
        // cut. Absent for most rounds, in which case there's nothing to
        // draw and short-siding reasoning falls back to green_center.
        if (hole.pin) {
          new mapboxgl.Marker({ color: "#c9a227" })
            .setLngLat([hole.pin.lng, hole.pin.lat])
            .addTo(map);
        }

        const shotsWithLocation = hole.shots.filter((shot) => shot.location !== null);
        for (const shot of shotsWithLocation) {
          new mapboxgl.Marker({
            color: shot.approach_leave === "short_sided" ? "#d03b3b" : "#2a78d6",
          })
            .setLngLat([shot.location!.lng, shot.location!.lat])
            .addTo(map);
        }

        if (shotsWithLocation.length > 0) {
          const coordinates: [number, number][] = [
            [hole.tee!.lng, hole.tee!.lat],
            ...shotsWithLocation.map(
              (shot) => [shot.location!.lng, shot.location!.lat] as [number, number]
            ),
          ];
          map.addSource("shot-path", {
            type: "geojson",
            data: {
              type: "Feature",
              properties: {},
              geometry: { type: "LineString", coordinates },
            },
          });
          map.addLayer({
            id: "shot-path-line",
            type: "line",
            source: "shot-path",
            paint: { "line-color": "#2a78d6", "line-width": 2 },
          });
        }
      });
    });

    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [token, hole]);

  if (!token || mapError) {
    return (
      <div>
        {!token && (
          <p className="mb-2 text-xs text-muted-foreground">
            Satellite imagery needs a Mapbox token (NEXT_PUBLIC_MAPBOX_TOKEN) — showing a
            schematic view instead.
          </p>
        )}
        {mapError && (
          <p className="mb-2 text-xs text-destructive" role="alert">
            Map failed to load: {mapError}
          </p>
        )}
        <HoleReplaySvg
          hole={hole}
          ellipse={ellipse}
          ellipseAnchorYards={ellipseAnchorYards}
          onPick={onPick}
          highlightedShotNumber={highlightedShotNumber}
        />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      data-testid="mapbox-container"
      className="h-[480px] w-full rounded-lg"
    />
  );
}
