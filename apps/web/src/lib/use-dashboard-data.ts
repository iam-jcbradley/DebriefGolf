"use client";

import useSWR from "swr";
import { getRoundAnalytics, getRounds, type RoundAnalyticsResponse, type RoundSummary } from "@/lib/api";

export type DashboardState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "ready"; round: RoundSummary; analytics: RoundAnalyticsResponse };

export interface UseDashboardData {
  state: DashboardState;
  refresh: () => void;
}

type DashboardFetch = { round: RoundSummary; analytics: RoundAnalyticsResponse } | null;

async function fetchDashboardRound(): Promise<DashboardFetch> {
  // Ask for one round rather than fetching every round the player has
  // ever played and sorting client-side: the API returns them newest
  // first, so the newest is the only one this page needs.
  const rounds = await getRounds({ limit: 1 });
  if (rounds.length === 0) return null;
  const round = rounds[0];
  const analytics = await getRoundAnalytics(round.id);
  return { round, analytics };
}

/** `userId`: scopes the SWR cache key so switching who's signed in (no
 * forced page reload — see current-user.tsx) can't briefly render the
 * previous player's cached round before revalidating. `null` when nobody's
 * signed in, which also disables the fetch entirely (SWR's key-is-null
 * convention). */
export function useDashboardData(userId: number | null): UseDashboardData {
  const { data, error, isLoading, mutate } = useSWR(
    userId !== null ? ["dashboard-round", userId] : null,
    fetchDashboardRound
  );

  let state: DashboardState;
  if (userId === null) {
    state = { status: "idle" };
  } else if (error) {
    state = {
      status: "error",
      message: error instanceof Error ? error.message : "Failed to load dashboard data",
    };
  } else if (isLoading) {
    state = { status: "loading" };
  } else if (data === null || data === undefined) {
    state = { status: "empty" };
  } else {
    state = { status: "ready", round: data.round, analytics: data.analytics };
  }

  return { state, refresh: () => void mutate() };
}
