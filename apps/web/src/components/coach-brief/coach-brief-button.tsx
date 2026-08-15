"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { getPracticeCombines, type RoundAnalytics, type RoundSummary } from "@/lib/api";

type ButtonState = "idle" | "generating" | "error";

export interface CoachBriefButtonProps {
  round: RoundSummary;
  analytics: RoundAnalytics;
}

/** Generates the 1-Page "Coach-Ready" Lesson Brief (PRD §7.2) client-side
 * and triggers a download. `@react-pdf/renderer` (and the document
 * definition) are only pulled in on click via a dynamic `import()` — same
 * bundle-size discipline as Mapbox (Phase 4/5) and the Practice Hub's
 * delivery trend chart, so visiting the dashboard never pays for a PDF
 * renderer nobody asked for.
 */
export function CoachBriefButton({ round, analytics }: CoachBriefButtonProps) {
  const [state, setState] = useState<ButtonState>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleClick() {
    setState("generating");
    try {
      const [{ pdf }, { CoachBriefDocument }] = await Promise.all([
        import("@react-pdf/renderer"),
        import("@/lib/coach-brief/coach-brief-document"),
      ]);
      // The coaching agenda reuses the same weakness -> combine mapping the
      // Practice Hub shows (app/services/practice_combines.py); a brand-new
      // player with no data on file yet still gets a brief, just an empty
      // agenda section.
      const combinesResult = await getPracticeCombines(round.user_id).catch(() => ({
        combines: [],
      }));

      const blob = await pdf(
        <CoachBriefDocument round={round} analytics={analytics} combines={combinesResult.combines} />
      ).toBlob();

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `debrief-golf-coach-brief-round-${round.id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setState("idle");
    } catch {
      setState("error");
      setErrorMessage("Failed to generate the coach brief.");
    }
  }

  return (
    <div>
      <Button
        type="button"
        variant="outline"
        onClick={() => void handleClick()}
        disabled={state === "generating"}
      >
        {state === "generating" ? "Generating…" : "Download Coach-Ready Brief"}
      </Button>
      {state === "error" && (
        <p className="mt-2 text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      )}
    </div>
  );
}
