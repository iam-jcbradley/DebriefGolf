"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { HoleReplayLegend } from "@/components/hole-replay/hole-replay-legend";
import { HoleReplayMap } from "@/components/hole-replay/hole-replay-map";
import { HoleShotList } from "@/components/hole-replay/hole-shot-list";
import { PinProvenanceNote } from "@/components/hole-replay/pin-provenance-note";
import { ShortSidedBanner } from "@/components/hole-replay/short-sided-banner";
import { SuckerPinAlert } from "@/components/hole-replay/sucker-pin-alert";
import { NavBar } from "@/components/nav-bar";
import { Overline } from "@/components/ui/overline";
import { cn } from "@/lib/utils";
import {
  ApiError,
  getHoleReplay,
  getRoundHoles,
  getSmartBag,
  type DispersionEllipse,
  type HoleReplay,
  type HoleSummary,
} from "@/lib/api";
import { pickApproachShot } from "@/lib/hole-replay/approach-club";
import { isWithinEllipse } from "@/lib/hole-replay/dispersion";
import { offsetFromAimLine } from "@/lib/hole-replay/projection";

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
  const [suckerPinClub, setSuckerPinClub] = useState<string | null>(null);
  const [highlightedShot, setHighlightedShot] = useState<number | null>(null);
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
    setSuckerPinClub(null);

    getHoleReplay(roundId, selectedHole)
      .then(async (result) => {
        if (cancelled) return;
        setReplay(result);

        const approachShot = pickApproachShot(result.shots);
        if (!approachShot?.club) return;
        // The bag is the session user's own; the round is theirs too or
        // this page would have 404ed before reaching here.
        const bag = await getSmartBag();
        if (cancelled) return;
        const clubStats = bag.clubs.find((c) => c.club === approachShot.club);
        if (cancelled) return;
        const ellipse = clubStats?.dispersion_ellipse ?? null;
        setEllipse(ellipse);
        // The ellipse's mean/stdev are carry distance *from where the shot
        // was struck*, so anchor it there rather than at the tee — see
        // HoleReplaySvgProps.ellipseAnchorYards.
        const anchor = {
          longitudinal: result.yardage - approachShot.start_distance_yards,
          lateral: 0,
        };
        setEllipseAnchorYards(anchor);

        // "Sucker pin" check (PRD §5.3): is today's actual pin inside this
        // club's typical dispersion pattern? Needs the same aim-line
        // projection the map itself uses, undoing `anchor` to land the pin
        // in the ellipse's own (unanchored) coordinate frame — the inverse
        // of how HoleReplaySvg positions the ellipse on screen.
        if (ellipse && result.pin && result.tee && result.green_center) {
          const pinOffset = offsetFromAimLine(result.tee, result.green_center, result.pin);
          const withinEllipse = isWithinEllipse(
            ellipse,
            pinOffset.longitudinalYards - anchor.longitudinal,
            pinOffset.lateralYards - anchor.lateral
          );
          setSuckerPinClub(withinEllipse ? approachShot.club : null);
        }
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
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Link href="/rounds" className="text-sm text-muted-foreground underline hover:text-foreground">
          &larr; Back to rounds
        </Link>
        <Overline accent className="mt-4">Round {roundId}</Overline>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight md:text-4xl">
          Hole replay
        </h1>

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
          <div className="mt-6 flex flex-wrap gap-1">
            {holes.map((hole) => (
              <button
                key={hole.hole_number}
                type="button"
                onClick={() => setSelectedHole(hole.hole_number)}
                aria-current={selectedHole === hole.hole_number}
                className={cn(
                  "rounded-sm border px-2.5 py-1 text-sm tabular-nums transition-colors",
                  selectedHole === hole.hole_number
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border hover:bg-muted"
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
            {suckerPinClub && <SuckerPinAlert club={suckerPinClub} />}

            {/* Canvas and shot detail side by side (PRD §8) — the numbers
                are what make the picture mean anything, and vice versa. */}
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div>
                <div className="flex items-baseline justify-between">
                  <Overline>
                    Hole {replay.hole_number} &middot; Par {replay.par}
                  </Overline>
                  <span className="text-sm text-muted-foreground tabular-nums">
                    {replay.yardage}y
                  </span>
                </div>
                <div className="mt-3">
                  <HoleReplayMap
                    hole={replay}
                    ellipse={ellipse}
                    ellipseAnchorYards={ellipseAnchorYards}
                    highlightedShotNumber={highlightedShot}
                  />
                </div>
                <HoleReplayLegend hasPin={replay.pin !== null} lateralExaggerated />
                <div className="mt-3">
                  <PinProvenanceNote
                    hasPin={replay.pin !== null}
                    hasGreenBoundary={replay.green_boundary !== null}
                  />
                </div>
              </div>

              <HoleShotList
                shots={replay.shots}
                highlightedShotNumber={highlightedShot}
                onHighlight={setHighlightedShot}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
