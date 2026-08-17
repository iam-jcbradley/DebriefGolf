"use client";

import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { Select } from "@/components/ui/select";
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

      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <label className="flex flex-col gap-1 text-sm">
          <Overline as="span">Hole</Overline>
          <Input
            type="number" min={1} max={18} value={holeNumber}
            onChange={(e) => setHoleNumber(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <Overline as="span">Club</Overline>
          <Input
            type="text" value={club} onChange={(e) => setClub(e.target.value)}
            placeholder="7-Iron / Putter"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <Overline as="span">Start lie</Overline>
          <Select value={startLie} onChange={(e) => setStartLie(e.target.value as Lie)}>
            {REVIEWABLE_LIES.map((lie) => (
              <option key={lie} value={lie}>{lie}</option>
            ))}
          </Select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <Overline as="span">End lie</Overline>
          <Select value={endLie} onChange={(e) => setEndLie(e.target.value as Lie)}>
            {LIES.map((lie) => (
              <option key={lie} value={lie}>{lie}</option>
            ))}
          </Select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <Overline as="span">Start distance (yd)</Overline>
          <Input
            type="number" min={0} step="any" value={startDistance}
            onChange={(e) => setStartDistance(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <Overline as="span">End distance (yd)</Overline>
          <Input
            type="number" min={0} step="any" value={endDistance}
            onChange={(e) => setEndDistance(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <Overline as="span">Strokes gained (optional)</Overline>
          <Input
            type="number" step="0.01" value={strokesGained}
            onChange={(e) => setStrokesGained(e.target.value)}
          />
        </label>
      </div>

      <Button type="submit" className="mt-3">
        Add shot
      </Button>
    </form>
  );
}
