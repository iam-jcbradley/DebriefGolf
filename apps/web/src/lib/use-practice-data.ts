"use client";

import useSWR from "swr";
import {
  ApiError,
  getDeliveryProfile,
  getPracticeCombines,
  type DeliveryProfile,
  type PracticeCombines,
} from "@/lib/api";

export type PracticeDataState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; delivery: DeliveryProfile; combines: PracticeCombines };

export interface UsePracticeData {
  state: PracticeDataState;
  refresh: () => void;
}

async function fetchPracticeData() {
  const [delivery, combines] = await Promise.all([getDeliveryProfile(), getPracticeCombines()]);
  return { delivery, combines };
}

/** Loads the Practice Hub's two data sources — delivery profile (PRD §6.1)
 * and prescriptive combines (PRD §7.1) — together, since both are scoped to
 * the session user and the page renders them side by side.
 *
 * `userId`: scopes the SWR cache key so switching who's signed in (no
 * forced page reload — see current-user.tsx) can't briefly render the
 * previous player's cached data before revalidating. `null` disables the
 * fetch entirely. */
export function usePracticeData(userId: number | null): UsePracticeData {
  const { data, error, isLoading, mutate } = useSWR(
    userId !== null ? ["practice-data", userId] : null,
    fetchPracticeData
  );

  let state: PracticeDataState;
  if (userId === null) {
    state = { status: "idle" };
  } else if (error) {
    state = {
      status: "error",
      message: error instanceof ApiError ? error.message : "Failed to load practice data",
    };
  } else if (isLoading || !data) {
    state = { status: "loading" };
  } else {
    state = { status: "ready", delivery: data.delivery, combines: data.combines };
  }

  return { state, refresh: () => void mutate() };
}
