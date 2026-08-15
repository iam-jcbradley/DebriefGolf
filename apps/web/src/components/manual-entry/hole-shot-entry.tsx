"use client";

import { useState, type FormEvent } from "react";
import { HoleReplayMap } from "@/components/hole-replay/hole-replay-map";
import type { HoleReplay, HoleReplayShot, LatLngPoint } from "@/lib/api";
import { LIES, type DraftShot, type Lie } from "@/lib/audit/types";

const REVIEWABLE_LIES = LIES.filter((lie) => lie !== "hole");

export type NewDraftShot = Omit<DraftShot, "id" | "holeNumber" | "shotNumber">;

export interface HoleShotEntryProps {
  hole: HoleReplay;
  /** Shots already added to this hole this session (not yet submitted to
   * the backend), rendered as map context alongside the pick-a-location
   * flow for the next one. */
  draftShotsForHole: DraftShot[];
  onAdd: (shot: NewDraftShot) => void;
}

/**
 * The manual-entry counterpart to the Phase 3 audit wizard's
 * `AddShotForm` — same shot fields, but adds a GPS location picked by
 * clicking the hole map (real Mapbox satellite when a token is configured,
 * the SVG schematic otherwise — both support clicking now, see
 * `HoleReplaySvgProps.onPick`/`HoleReplayMapProps.onPick`) rather than no
 * location at all. Used once a round has a real course attached, so real
 * tee/green geometry exists to click against.
 */
export function HoleShotEntry({ hole, draftShotsForHole, onAdd }: HoleShotEntryProps) {
  const [club, setClub] = useState("");
  const [startLie, setStartLie] = useState<Lie>("fairway");
  const [endLie, setEndLie] = useState<Lie>("green");
  const [startDistance, setStartDistance] = useState("");
  const [endDistance, setEndDistance] = useState("");
  const [tag, setTag] = useState("");
  const [location, setLocation] = useState<LatLngPoint | null>(null);

  const previewShots: HoleReplayShot[] = draftShotsForHole.map((shot, index) => ({
    shot_id: -(index + 1), // negative — these aren't persisted yet, just local preview
    shot_number: shot.shotNumber,
    club: shot.club,
    start_lie: shot.startLie,
    end_lie: shot.endLie,
    start_distance_yards: shot.startDistanceYards,
    end_distance_yards: shot.endDistanceYards,
    strokes_gained: null,
    tag: shot.tag ?? null,
    approach_leave: "unclassified",
    location: shot.location ?? null,
  }));

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const start = Number(startDistance);
    const end = Number(endDistance);
    if (Number.isNaN(start) || Number.isNaN(end)) return;

    onAdd({
      club: club.trim() || null,
      startLie,
      endLie,
      startDistanceYards: start,
      endDistanceYards: end,
      location,
      tag: tag.trim() || undefined,
    });

    setClub("");
    setStartDistance("");
    setEndDistance("");
    setTag("");
    setLocation(null);
  }

  return (
    <div className="space-y-3">
      <HoleReplayMap hole={{ ...hole, shots: previewShots }} onPick={setLocation} />

      {location ? (
        <p className="text-xs text-muted-foreground">
          Location set ({location.lat.toFixed(5)}, {location.lng.toFixed(5)}) —{" "}
          <button type="button" onClick={() => setLocation(null)} className="underline">
            clear
          </button>
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">
          Click the map to set this shot&apos;s GPS location (optional).
        </p>
      )}

      <form onSubmit={handleSubmit} className="rounded-lg border p-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <label className="text-sm">
            Club
            <input
              type="text"
              value={club}
              onChange={(e) => setClub(e.target.value)}
              placeholder="7-Iron / Putter"
              className="mt-1 w-full rounded-md border bg-background px-2 py-1"
            />
          </label>
          <label className="text-sm">
            Start lie
            <select
              value={startLie}
              onChange={(e) => setStartLie(e.target.value as Lie)}
              className="mt-1 w-full rounded-md border bg-background px-2 py-1"
            >
              {REVIEWABLE_LIES.map((lie) => (
                <option key={lie} value={lie}>
                  {lie}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            End lie
            <select
              value={endLie}
              onChange={(e) => setEndLie(e.target.value as Lie)}
              className="mt-1 w-full rounded-md border bg-background px-2 py-1"
            >
              {LIES.map((lie) => (
                <option key={lie} value={lie}>
                  {lie}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Start distance (yd)
            <input
              type="number"
              min={0}
              step="any"
              value={startDistance}
              onChange={(e) => setStartDistance(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-2 py-1"
            />
          </label>
          <label className="text-sm">
            End distance (yd)
            <input
              type="number"
              min={0}
              step="any"
              value={endDistance}
              onChange={(e) => setEndDistance(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-2 py-1"
            />
          </label>
          <label className="text-sm">
            Tag (optional)
            <input
              type="text"
              value={tag}
              onChange={(e) => setTag(e.target.value)}
              placeholder="OB Right"
              className="mt-1 w-full rounded-md border bg-background px-2 py-1"
            />
          </label>
        </div>

        <button
          type="submit"
          className="mt-3 rounded-md border bg-primary px-4 py-2 text-sm text-primary-foreground hover:opacity-90"
        >
          Add shot
        </button>
      </form>
    </div>
  );
}
