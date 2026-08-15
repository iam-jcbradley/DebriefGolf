"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { HoleReplayMap } from "@/components/hole-replay/hole-replay-map";
import { ShortSidedBanner } from "@/components/hole-replay/short-sided-banner";
import { NavBar } from "@/components/nav-bar";
import { cn } from "@/lib/utils";
import {
  ApiError,
  getHoleReplay,
  getRoundHoles,
  getRounds,
  getSmartBag,
  type DispersionEllipse,
  type HoleReplay,
  type HoleSummary,
} from "@/lib/api";
import { pickApproachShot } from "@/lib/hole-replay/approach-club";

export default function RoundDetailPage() {
  const params = useParams<{ id: string }>();
  const roundId = Number(params.id);

  const [holes, setHoles] = useState<HoleSummary[] | null>(null);
  const [selectedHole, setSelectedHole] = useState<number | null>(null);
  const [replay, setReplay] = useState<HoleReplay | null>(null);
  const [ellipse, setEllipse] = useState<DispersionEllipse | null>(null);
  const [ellipseAnchorYards, setEllipseAnchorYards] = useState<
    { longitudinal: number; lateral: number } | null
  >(null);
  const [error, setError] = useState<string | null>(null);

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
    setReplay(null);
    setEllipse(null);
    setEllipseAnchorYards(null);

    getHoleReplay(roundId, selectedHole)
      .then(async (result) => {
        if (cancelled) return;
        setReplay(result);

        const approachShot = pickApproachShot(result.shots);
        if (!approachShot?.club) return;
        const rounds = await getRounds();
        const round = rounds.find((r) => r.id === roundId);
        if (!round || cancelled) return;
        const bag = await getSmartBag(round.user_id);
        const clubStats = bag.clubs.find((c) => c.club === approachShot.club);
        if (cancelled) return;
        setEllipse(clubStats?.dispersion_ellipse ?? null);
        // The ellipse's mean/stdev are carry distance *from where the shot
        // was struck*, so anchor it there rather than at the tee — see
        // HoleReplaySvgProps.ellipseAnchorYards.
        setEllipseAnchorYards({
          longitudinal: result.yardage - approachShot.start_distance_yards,
          lateral: 0,
        });
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load hole replay");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [roundId, selectedHole]);

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Round #{roundId} — Hole Replay</h1>

        {error && (
          <p role="alert" className="mt-4 text-destructive">
            {error}
          </p>
        )}

        {holes && holes.length === 0 && (
          <p className="mt-4 text-muted-foreground">
            This round has no course assigned yet, so there&apos;s no hole geometry to replay.
          </p>
        )}

        {holes && holes.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1">
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
              </button>
            ))}
          </div>
        )}

        {replay && (
          <div className="mt-6 space-y-4">
            <ShortSidedBanner
              holeNumber={replay.hole_number}
              shortSidedCount={replay.short_sided_count}
            />
            <p className="text-sm text-muted-foreground">
              Par {replay.par} · {replay.yardage}y
            </p>
            <HoleReplayMap hole={replay} ellipse={ellipse} ellipseAnchorYards={ellipseAnchorYards} />
          </div>
        )}
      </main>
    </div>
  );
}
