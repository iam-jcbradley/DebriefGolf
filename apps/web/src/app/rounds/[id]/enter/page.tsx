"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { HoleShotEntry, type NewDraftShot } from "@/components/manual-entry/hole-shot-entry";
import { NavBar } from "@/components/nav-bar";
import { Overline } from "@/components/ui/overline";
import {
  ApiError,
  getHoleReplay,
  getRoundHoles,
  submitRoundPins,
  submitRoundShots,
  type HoleReplay,
  type HoleSummary,
  type LatLngPoint,
  type ShotCreateInput,
} from "@/lib/api";
import type { DraftShot } from "@/lib/audit/types";
import { useAuditDraft } from "@/lib/audit/use-audit-draft";
import { cn } from "@/lib/utils";

export default function EnterRoundPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const roundId = Number(params.id);

  const [holes, setHoles] = useState<HoleSummary[] | null>(null);
  const [selectedHole, setSelectedHole] = useState<number | null>(null);
  const [holeReplay, setHoleReplay] = useState<HoleReplay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { shots, setShots, loaded, clear } = useAuditDraft(roundId, []);

  useEffect(() => {
    let cancelled = false;
    getRoundHoles(roundId)
      .then((result) => {
        if (cancelled) return;
        setHoles(result);
        if (result.length > 0) setSelectedHole(result[0].hole_number);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load holes");
      });
    return () => {
      cancelled = true;
    };
  }, [roundId]);

  useEffect(() => {
    if (selectedHole === null) return;
    let cancelled = false;
    setHoleReplay(null);
    getHoleReplay(roundId, selectedHole)
      .then((result) => {
        if (!cancelled) setHoleReplay(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load hole geometry");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [roundId, selectedHole]);

  function nextShotNumberForHole(holeNumber: number): number {
    return shots.filter((shot) => shot.holeNumber === holeNumber).length + 1;
  }

  function handleAdd(shot: NewDraftShot) {
    if (selectedHole === null) return;
    setShots([
      ...shots,
      {
        ...shot,
        id: crypto.randomUUID(),
        holeNumber: selectedHole,
        shotNumber: nextShotNumberForHole(selectedHole),
      },
    ]);
  }

  function removeShot(id: string) {
    setShots(shots.filter((shot) => shot.id !== id));
  }

  async function handleSetPin(latlng: LatLngPoint) {
    if (selectedHole === null) return;
    try {
      const [pin] = await submitRoundPins(roundId, [
        { hole_number: selectedHole, location: latlng },
      ]);
      setHoleReplay((current) => (current ? { ...current, pin: pin.location } : current));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save the pin");
    }
  }

  async function handleSubmitRound() {
    setSubmitting(true);
    setError(null);
    try {
      const payload: ShotCreateInput[] = shots.map((shot: DraftShot) => ({
        hole_number: shot.holeNumber,
        shot_number: shot.shotNumber,
        club: shot.club,
        start_lie: shot.startLie,
        end_lie: shot.endLie,
        start_distance_yards: shot.startDistanceYards,
        end_distance_yards: shot.endDistanceYards,
        location: shot.location ?? null,
        tag: shot.tag ?? null,
      }));
      await submitRoundShots(roundId, payload);
      await clear();
      router.push(`/rounds/${roundId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit round");
    } finally {
      setSubmitting(false);
    }
  }

  const shotsForSelectedHole =
    selectedHole === null ? [] : shots.filter((shot) => shot.holeNumber === selectedHole);

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-3xl space-y-6 px-6 py-10">
        <div>
          <Link href="/rounds" className="text-sm text-muted-foreground underline hover:text-foreground">
            &larr; Back to rounds
          </Link>
          <Overline accent className="mt-4">Round {roundId}</Overline>
          <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight md:text-4xl">
            Enter shots
          </h1>
          <p className="mt-3 max-w-prose text-sm text-muted-foreground">
            Click the map to set each shot&apos;s GPS location, then submit the whole round once
            you&apos;re done.
          </p>
        </div>

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}

        {holes && holes.length === 0 && (
          <p className="text-sm text-muted-foreground">
            This round&apos;s course has no holes yet.
          </p>
        )}

        {holes && holes.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {holes.map((hole) => (
              <button
                key={hole.hole_number}
                type="button"
                onClick={() => setSelectedHole(hole.hole_number)}
                aria-current={selectedHole === hole.hole_number}
                className={cn(
                  "rounded-md border px-2.5 py-1 text-sm",
                  selectedHole === hole.hole_number
                    ? "border-primary bg-primary text-primary-foreground"
                    : "hover:bg-muted"
                )}
              >
                {hole.hole_number}
                {shots.some((shot) => shot.holeNumber === hole.hole_number) && " •"}
              </button>
            ))}
          </div>
        )}

        {holeReplay && loaded && (
          <HoleShotEntry
            hole={holeReplay}
            draftShotsForHole={shotsForSelectedHole}
            onAdd={handleAdd}
            onSetPin={handleSetPin}
          />
        )}

        {shotsForSelectedHole.length > 0 && (
          <div className="rounded-lg border p-4">
            <p className="text-sm font-medium">
              Hole {selectedHole} — {shotsForSelectedHole.length} shot
              {shotsForSelectedHole.length === 1 ? "" : "s"}
            </p>
            <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
              {shotsForSelectedHole.map((shot) => (
                <li key={shot.id} className="flex items-center justify-between gap-2">
                  <span>
                    {shot.club ?? "—"} · {shot.startLie} {shot.startDistanceYards}y →{" "}
                    {shot.endLie} {shot.endDistanceYards}y{shot.location ? " · pinned" : ""}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeShot(shot.id)}
                    className="shrink-0 text-xs text-destructive underline"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {shots.length > 0 && (
          <button
            type="button"
            onClick={handleSubmitRound}
            disabled={submitting}
            className="rounded-md border bg-primary px-4 py-2 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Submitting…" : `Submit round (${shots.length} shots)`}
          </button>
        )}
      </main>
    </div>
  );
}
