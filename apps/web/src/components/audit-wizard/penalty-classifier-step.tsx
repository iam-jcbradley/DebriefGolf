"use client";

import { Button } from "@/components/ui/button";
import {
  classifyPenaltyDrop,
  type PenaltyDropContext,
  type PenaltyDropResult,
  type PenaltyType,
} from "@/lib/audit/penalty-classifier";

export interface PenaltyClassifierStepProps {
  context: PenaltyDropContext;
  onClassified: (result: PenaltyDropResult) => void;
}

export function PenaltyClassifierStep({ context, onClassified }: PenaltyClassifierStepProps) {
  function choose(type: PenaltyType) {
    onClassified(classifyPenaltyDrop(type, context));
  }

  return (
    <div role="group" aria-label="Penalty drop classification" className="rounded-lg border p-4">
      <p className="text-sm font-medium">How was this penalty taken?</p>
      <p className="mt-1 text-sm text-muted-foreground">
        This changes where the next shot is recorded from.
      </p>
      <div className="mt-3 flex gap-2">
        <Button type="button" variant="outline" onClick={() => choose("lateral_hazard")}>
          Lateral Hazard
        </Button>
        <Button type="button" variant="outline" onClick={() => choose("ob_lost_ball")}>
          OB / Lost Ball
        </Button>
      </div>
    </div>
  );
}
