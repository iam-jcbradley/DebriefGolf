"use client";

import "mapbox-gl/dist/mapbox-gl.css";
import { useEffect, useRef, useState } from "react";
import { CourseGeometryMapSvg } from "@/components/course-builder/course-geometry-map-svg";
import type { LatLng } from "@/lib/hole-replay/projection";

const ENV_MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

export interface CourseGeometryMapProps {
  center: LatLng;
  tee: LatLng | null;
  green: LatLng | null;
  boundary: LatLng[];
  onPick: (latlng: LatLng) => void;
  /** Overrides the NEXT_PUBLIC_MAPBOX_TOKEN env var — mainly for tests. */
  mapboxToken?: string;
}

/**
 * Course-builder counterpart to `hole-replay/HoleReplayMap`, same
 * progressive-enhancement shape: real Mapbox satellite imagery with a
 * click handler when a token is configured, falling back to
 * `CourseGeometryMapSvg` otherwise or on a map load error. Unlike the
 * read-only hole-replay map, this one is interactive — clicking places a
 * point (which point depends on the placement mode the caller tracks, see
 * `HoleGeometryEditor`) — so it keeps the underlying `mapboxgl.Map` and its
 * markers alive across re-renders instead of tearing the map down on every
 * point placed.
 */
export function CourseGeometryMap({
  center,
  tee,
  green,
  boundary,
  onPick,
  mapboxToken,
}: CourseGeometryMapProps) {
  const token = mapboxToken ?? ENV_MAPBOX_TOKEN;
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("mapbox-gl").Map | null>(null);
  const markersRef = useRef<import("mapbox-gl").Marker[]>([]);
  // Keeps the click handler registered once (in the mount effect) reading
  // the latest `onPick` without re-creating the map every time the parent
  // re-renders with a new function identity.
  const onPickRef = useRef(onPick);
  useEffect(() => {
    onPickRef.current = onPick;
  });

  const [mapError, setMapError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    if (!token || !containerRef.current) return;

    let cancelled = false;
    let map: import("mapbox-gl").Map | undefined;

    import("mapbox-gl").then(({ default: mapboxgl }) => {
      if (cancelled || !containerRef.current) return;

      mapboxgl.accessToken = token;
      map = new mapboxgl.Map({
        container: containerRef.current,
        style: "mapbox://styles/mapbox/satellite-streets-v12",
        center: [center.lng, center.lat],
        zoom: 17,
      });
      mapRef.current = map;

      map.on("error", (event) => setMapError(event.error?.message ?? "Failed to load the map"));
      map.on("click", (event) => onPickRef.current({ lat: event.lngLat.lat, lng: event.lngLat.lng }));
      map.on("load", () => setMapReady(true));
    });

    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
      setMapReady(false);
    };
    // Deliberately just `token`: re-centering the live map whenever `center`
    // changes would fight the user's own panning once they're placing
    // points. A genuinely different course gets a fresh map via a React
    // `key` from the parent, not a prop change here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    const map = mapRef.current;
    let cancelled = false;

    import("mapbox-gl").then(({ default: mapboxgl }) => {
      if (cancelled) return;
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];

      if (tee) {
        markersRef.current.push(
          new mapboxgl.Marker({ color: "#0b0b0b" }).setLngLat([tee.lng, tee.lat]).addTo(map)
        );
      }
      if (green) {
        markersRef.current.push(
          new mapboxgl.Marker({ color: "#2a9d5c" }).setLngLat([green.lng, green.lat]).addTo(map)
        );
      }
      for (const point of boundary) {
        markersRef.current.push(
          new mapboxgl.Marker({ color: "#d08a00" }).setLngLat([point.lng, point.lat]).addTo(map)
        );
      }
    });

    return () => {
      cancelled = true;
    };
  }, [mapReady, tee, green, boundary]);

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
        <CourseGeometryMapSvg center={center} tee={tee} green={green} boundary={boundary} onPick={onPick} />
      </div>
    );
  }

  return (
    <div ref={containerRef} data-testid="mapbox-container" className="h-[400px] w-full rounded-lg" />
  );
}
