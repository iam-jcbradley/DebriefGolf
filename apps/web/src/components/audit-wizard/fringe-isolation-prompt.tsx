"use client";

import { Button } from "@/components/ui/button";
import {
  needsFringeIsolationPrompt,
  resolveFringeIsolation,
  type FringeIsolationChoice,
} from "@/lib/audit/putt-routing";
import type { Lie } from "@/lib/audit/types";

export interface FringeIsolationPromptProps {
  club: string | null;
  startLie: Lie;
  onResolved: (lie: Lie) => void;
}

export function FringeIsolationPrompt({ club, startLie, onResolved }: FringeIsolationPromptProps) {
  if (!needsFringeIsolationPrompt(club, startLie)) return null;

  function choose(choice: FringeIsolationChoice) {
    onResolved(resolveFringeIsolation(choice, startLie));
  }

  return (
    <div role="group" aria-label="Fringe vs. true putting isolation" className="rounded-lg border p-4">
      <p className="text-sm font-medium">Was this putt actually on the green?</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Putts from the fringe count differently than true green putts.
      </p>
      <div className="mt-3 flex gap-2">
        <Button type="button" variant="outline" onClick={() => choose("true_putt")}>
          Count as true putt
        </Button>
        <Button type="button" variant="outline" onClick={() => choose("fringe_short_game")}>
          Count as short game
        </Button>
      </div>
    </div>
  );
}
