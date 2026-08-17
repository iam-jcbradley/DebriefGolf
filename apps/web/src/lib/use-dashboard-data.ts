"use client";

import useSWR from "swr";
import {
  getRoundAnalytics,
  getRoundHoles,
  getRounds,
  type RoundAnalyticsResponse,
  type RoundSummary,
} from "@/lib/api";

export type DashboardState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      round: RoundSummary;
      analytics: RoundAnalyticsResponse;
      /** Sum of par for the holes this round was played over, so the
       * snapshot can show score-to-par (PRD §8's "78 (+6)"). `null` when
       * the round has no course attached and there are no holes to sum. */
      coursePar: number | null;
    };

export interface UseDashboardData {
  state: DashboardState;
  refresh: () => void;
}

type DashboardFetch = {
  round: RoundSummary;
  analytics: RoundAnalyticsResponse;
  coursePar: number | null;
} | null;

async function fetchDashboardRound(): Promise<DashboardFetch> {
  // Ask for one round rather than fetching every round the player has
  // ever played and sorting client-side: the API returns them newest
  // first, so the newest is the only one this page needs.
  const rounds = await getRounds({ limit: 1 });
  if (rounds.length === 0) return null;
  const round = rounds[0];

  // Holes come along for their `par` only. A round with no course 409s or
  // returns nothing here, which is not a dashboard error — the snapshot
  // just renders without a to-par figure.
  const [analytics, holes] = await Promise.all([
    getRoundAnalytics(round.id),
    getRoundHoles(round.id).catch(() => []),
  ]);
  const coursePar = holes.length > 0 ? holes.reduce((sum, h) => sum + h.par, 0) : null;

  return { round, analytics, coursePar };
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
    state = {
      status: "ready",
      round: data.round,
      analytics: data.analytics,
      coursePar: data.coursePar,
    };
  }

  return { state, refresh: () => void mutate() };
}
