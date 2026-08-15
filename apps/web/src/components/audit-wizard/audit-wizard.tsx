"use client";

import { FringeIsolationPrompt } from "@/components/audit-wizard/fringe-isolation-prompt";
import { PenaltyClassifierStep } from "@/components/audit-wizard/penalty-classifier-step";
import { PuttRoutingStep } from "@/components/audit-wizard/putt-routing-step";
import { StrikeQualityModal } from "@/components/audit-wizard/strike-quality-modal";
import {
  applyFringeIsolationResolution,
  applyPenaltyResolution,
  applyPuttRoutingResolution,
  applyStrikeQualityResolution,
  computeReviewQueue,
  markReviewed,
} from "@/lib/audit/review-queue";
import type { DraftShot } from "@/lib/audit/types";
import { useAuditDraft } from "@/lib/audit/use-audit-draft";

export interface AuditWizardProps {
  roundId: number;
  initialShots: DraftShot[];
}

export function AuditWizard({ roundId, initialShots }: AuditWizardProps) {
  const { shots, setShots, loaded } = useAuditDraft(roundId, initialShots);

  if (!loaded) {
    return <p className="text-sm text-muted-foreground">Loading your draft…</p>;
  }

  const queue = computeReviewQueue(shots);

  if (queue.length === 0) {
    return (
      <div className="rounded-lg border p-4">
        <p className="text-sm font-medium">All caught up</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Every shot in this round has been reviewed. Submitting a reviewed round back to
          Debrief Golf needs a course assigned to it first — that flow isn&apos;t built yet
          (see docs/DEVELOPMENT_PLAN.md Phase 3/4).
        </p>
      </div>
    );
  }

  const current = queue[0];
  const currentShot = shots.find((shot) => shot.id === current.shotId);
  if (!currentShot) return null; // the queue is derived from `shots`, so this can't happen

  const remaining = queue.length;

  return (
    <div>
      <p className="mb-2 text-sm text-muted-foreground">
        {remaining} shot{remaining === 1 ? "" : "s"} to review · Hole {currentShot.holeNumber},
        shot {currentShot.shotNumber}
      </p>

      {current.type === "penalty" && (
        <PenaltyClassifierStep
          context={{
            precedingShotStartLie: currentShot.startLie,
            precedingShotStartDistanceYards: currentShot.startDistanceYards,
            enteredHazardDistanceYards: currentShot.endDistanceYards,
          }}
          onClassified={(result) =>
            setShots(applyPenaltyResolution(shots, currentShot.id, result.penaltyType))
          }
        />
      )}

      {current.type === "fringe_isolation" && (
        <FringeIsolationPrompt
          club={currentShot.club}
          startLie={currentShot.startLie}
          onResolved={(lie) => setShots(applyFringeIsolationResolution(shots, currentShot.id, lie))}
        />
      )}

      {current.type === "putt_routing" && (
        <PuttRoutingStep
          startDistanceYards={currentShot.startDistanceYards}
          onShortPuttResult={(made) =>
            setShots(applyPuttRoutingResolution(shots, currentShot.id, { made }))
          }
          onLongPuttResult={(feet) =>
            setShots(applyPuttRoutingResolution(shots, currentShot.id, { lagProximityFeet: feet }))
          }
          onContinue={() => setShots(markReviewed(shots, currentShot.id, "putt_routing"))}
        />
      )}

      {current.type === "strike_quality" && currentShot.strokesGained !== undefined && (
        <StrikeQualityModal
          open
          strokesGained={currentShot.strokesGained}
          onTag={(tag) => setShots(applyStrikeQualityResolution(shots, currentShot.id, tag))}
          onSkip={() => setShots(markReviewed(shots, currentShot.id, "strike_quality"))}
        />
      )}
    </div>
  );
}
