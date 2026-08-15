"use client";

import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { LIES, type DraftShot, type Lie } from "@/lib/audit/types";

export interface AddShotFormProps {
  nextShotNumberForHole: (holeNumber: number) => number;
  onAdd: (shot: DraftShot) => void;
}

const REVIEWABLE_LIES = LIES.filter((lie) => lie !== "hole");

export function AddShotForm({ nextShotNumberForHole, onAdd }: AddShotFormProps) {
  const [holeNumber, setHoleNumber] = useState("1");
  const [club, setClub] = useState("");
  const [startLie, setStartLie] = useState<Lie>("fairway");
  const [endLie, setEndLie] = useState<Lie>("green");
  const [startDistance, setStartDistance] = useState("");
  const [endDistance, setEndDistance] = useState("");
  const [strokesGained, setStrokesGained] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const hole = Number(holeNumber);
    const start = Number(startDistance);
    const end = Number(endDistance);
    if (Number.isNaN(hole) || Number.isNaN(start) || Number.isNaN(end)) return;

    onAdd({
      id: crypto.randomUUID(),
      holeNumber: hole,
      shotNumber: nextShotNumberForHole(hole),
      club: club.trim() || null,
      startLie,
      endLie,
      startDistanceYards: start,
      endDistanceYards: end,
      strokesGained: strokesGained.trim() === "" ? undefined : Number(strokesGained),
    });

    setClub("");
    setStartDistance("");
    setEndDistance("");
    setStrokesGained("");
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border p-4">
      <p className="text-sm font-medium">Add a shot</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Strokes gained is normally computed by the backend once a round has a course assigned
        — enter one here to preview how the strike-quality prompt reacts to it.
      </p>

      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <label className="text-sm">
          Hole
          <input
            type="number" min={1} max={18} value={holeNumber}
            onChange={(e) => setHoleNumber(e.target.value)}
            className="mt-1 w-full rounded-md border bg-background px-2 py-1"
          />
        </label>
        <label className="text-sm">
          Club
          <input
            type="text" value={club} onChange={(e) => setClub(e.target.value)}
            placeholder="7-Iron / Putter"
            className="mt-1 w-full rounded-md border bg-background px-2 py-1"
          />
        </label>
        <label className="text-sm">
          Start lie
          <select
            value={startLie} onChange={(e) => setStartLie(e.target.value as Lie)}
            className="mt-1 w-full rounded-md border bg-background px-2 py-1"
          >
            {REVIEWABLE_LIES.map((lie) => (
              <option key={lie} value={lie}>{lie}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          End lie
          <select
            value={endLie} onChange={(e) => setEndLie(e.target.value as Lie)}
            className="mt-1 w-full rounded-md border bg-background px-2 py-1"
          >
            {LIES.map((lie) => (
              <option key={lie} value={lie}>{lie}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Start distance (yd)
          <input
            type="number" min={0} step="any" value={startDistance}
            onChange={(e) => setStartDistance(e.target.value)}
            className="mt-1 w-full rounded-md border bg-background px-2 py-1"
          />
        </label>
        <label className="text-sm">
          End distance (yd)
          <input
            type="number" min={0} step="any" value={endDistance}
            onChange={(e) => setEndDistance(e.target.value)}
            className="mt-1 w-full rounded-md border bg-background px-2 py-1"
          />
        </label>
        <label className="text-sm">
          Strokes gained (optional)
          <input
            type="number" step="0.01" value={strokesGained}
            onChange={(e) => setStrokesGained(e.target.value)}
            className="mt-1 w-full rounded-md border bg-background px-2 py-1"
          />
        </label>
      </div>

      <Button type="submit" className="mt-3">
        Add shot
      </Button>
    </form>
  );
}
