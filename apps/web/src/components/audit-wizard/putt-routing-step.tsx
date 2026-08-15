"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { routePutt } from "@/lib/audit/putt-routing";

export interface PuttRoutingStepProps {
  startDistanceYards: number;
  onShortPuttResult: (made: boolean) => void;
  onLongPuttResult: (proximityFeet: number) => void;
  onContinue?: () => void;
}

export function PuttRoutingStep({
  startDistanceYards,
  onShortPuttResult,
  onLongPuttResult,
  onContinue,
}: PuttRoutingStepProps) {
  const route = routePutt(startDistanceYards);
  const [proximity, setProximity] = useState("");

  if (route === "short_putt") {
    return (
      <div role="group" aria-label="Short putt result" className="rounded-lg border p-4">
        <p className="text-sm font-medium">Did this putt go in?</p>
        <div className="mt-3 flex gap-2">
          <Button type="button" onClick={() => onShortPuttResult(true)}>
            Made it
          </Button>
          <Button type="button" variant="outline" onClick={() => onShortPuttResult(false)}>
            Missed
          </Button>
        </div>
      </div>
    );
  }

  if (route === "long_putt") {
    return (
      <div role="group" aria-label="Long putt lag proximity" className="rounded-lg border p-4">
        <label htmlFor="lag-proximity" className="text-sm font-medium">
          How close did you leave it? (feet)
        </label>
        <div className="mt-2 flex gap-2">
          <input
            id="lag-proximity"
            type="number"
            min={0}
            value={proximity}
            onChange={(event) => setProximity(event.target.value)}
            className="w-24 rounded-md border bg-background px-2 py-1"
          />
          <Button
            type="button"
            onClick={() => {
              const feet = Number(proximity);
              if (!Number.isNaN(feet)) onLongPuttResult(feet);
            }}
            disabled={proximity.trim() === ""}
          >
            Save
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div role="group" aria-label="Putt review" className="rounded-lg border p-4">
      <p className="text-sm text-muted-foreground">No special review needed for this putt.</p>
      {onContinue && (
        <Button type="button" className="mt-2" onClick={onContinue}>
          Continue
        </Button>
      )}
    </div>
  );
}
