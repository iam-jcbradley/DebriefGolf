"use client";

import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { ApiError, createVirtualRound, type SimPlatform, type VirtualRound } from "@/lib/api";

const PLATFORMS: { value: SimPlatform; label: string }[] = [
  { value: "home_tee_hero", label: "Home Tee Hero" },
  { value: "e6", label: "E6" },
  { value: "gspro", label: "GSPro" },
  { value: "other", label: "Other" },
];

export interface VirtualRoundFormProps {
  onCreated?: (round: VirtualRound) => void;
}

/** Logs a simulator round (PRD §6.2). Scorecard-level only — see
 * `app.models.virtual_round.VirtualRound` for why this stays a separate
 * table from `Round` rather than a flag on it. */
export function VirtualRoundForm({ onCreated }: VirtualRoundFormProps) {
  const [platform, setPlatform] = useState<SimPlatform>("gspro");
  const [courseName, setCourseName] = useState("");
  const [totalScore, setTotalScore] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (courseName.trim() === "") {
      setStatus("error");
      setErrorMessage("Enter a course name.");
      return;
    }

    setStatus("saving");
    try {
      const round = await createVirtualRound({
        platform,
        course_name: courseName.trim(),
        total_score: totalScore.trim() === "" ? null : Number(totalScore),
      });
      setStatus("idle");
      setCourseName("");
      setTotalScore("");
      onCreated?.(round);
    } catch (error) {
      setStatus("error");
      setErrorMessage(error instanceof ApiError ? error.message : "Failed to save round.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
      <label className="flex flex-col gap-1 text-sm" htmlFor="virtual-round-platform">
        <Overline as="span">Platform</Overline>
        <select
          id="virtual-round-platform"
          value={platform}
          onChange={(event) => setPlatform(event.target.value as SimPlatform)}
          className="border-0 border-b border-border bg-transparent py-1 text-sm outline-none focus-visible:border-primary"
        >
          {PLATFORMS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm" htmlFor="virtual-round-course">
        <Overline as="span">Course</Overline>
        <Input
          id="virtual-round-course"
          value={courseName}
          onChange={(event) => setCourseName(event.target.value)}
          placeholder="Pebble Beach"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm" htmlFor="virtual-round-score">
        <Overline as="span">Total score</Overline>
        <Input
          id="virtual-round-score"
          type="number"
          value={totalScore}
          onChange={(event) => setTotalScore(event.target.value)}
        />
      </label>

      <div className="flex items-end">
        <Button type="submit" disabled={status === "saving"}>
          {status === "saving" ? "Saving…" : "Log round"}
        </Button>
      </div>

      {status === "error" && (
        <p className="sm:col-span-2 text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      )}
    </form>
  );
}
