"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AddShotForm } from "@/components/audit-wizard/add-shot-form";
import { AuditWizard } from "@/components/audit-wizard/audit-wizard";
import { NavBar } from "@/components/nav-bar";
import { Button } from "@/components/ui/button";
import { Overline } from "@/components/ui/overline";
import type { DraftShot } from "@/lib/audit/types";

export default function RoundAuditPage() {
  const params = useParams<{ id: string }>();
  const roundId = Number(params.id);
  const [shots, setShots] = useState<DraftShot[]>([]);
  const [reviewing, setReviewing] = useState(false);

  function nextShotNumberForHole(holeNumber: number): number {
    return shots.filter((shot) => shot.holeNumber === holeNumber).length + 1;
  }

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
            Audit round
          </h1>
          <p className="mt-3 max-w-prose text-sm text-muted-foreground">
            Enter this round&apos;s shots, then work through anything the wizard flags for
            review.
          </p>
        </div>

        {!reviewing && (
          <>
            <AddShotForm
              nextShotNumberForHole={nextShotNumberForHole}
              onAdd={(shot) => setShots((prev) => [...prev, shot])}
            />
            {shots.length > 0 && (
              <div className="rounded-lg border p-4">
                <p className="text-sm font-medium">
                  {shots.length} shot{shots.length === 1 ? "" : "s"} entered
                </p>
                <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                  {shots.map((shot) => (
                    <li key={shot.id}>
                      Hole {shot.holeNumber} · {shot.club ?? "—"} · {shot.startLie}{" "}
                      {shot.startDistanceYards}y → {shot.endLie} {shot.endDistanceYards}y
                    </li>
                  ))}
                </ul>
                <Button type="button" className="mt-3" onClick={() => setReviewing(true)}>
                  Start audit review
                </Button>
              </div>
            )}
          </>
        )}

        {reviewing && <AuditWizard roundId={roundId} initialShots={shots} />}
      </main>
    </div>
  );
}
