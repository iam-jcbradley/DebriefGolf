"use client";

import { useCallback, useEffect, useState } from "react";
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

function mostRecent(rounds: RoundSummary[]): RoundSummary {
  return [...rounds].sort(
    (a, b) => new Date(b.played_at).getTime() - new Date(a.played_at).getTime()
  )[0];
}

/** `userId`: the current player (`useCurrentUser`). Rounds are always
 * fetched scoped to them — an unfiltered list would show whichever
 * player's round happens to be most recent globally, which stopped making
 * sense the moment player identity became a real, persisted thing rather
 * than "whoever last typed a number in". */
export function useDashboardData(userId: number | null): UseDashboardData {
  const [state, setState] = useState<DashboardState>({ status: "idle" });
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (userId === null) {
      setState({ status: "idle" });
      return;
    }
    let cancelled = false;

    async function load() {
      setState({ status: "loading" });
      try {
        const rounds = await getRounds(userId as number);
        if (rounds.length === 0) {
          if (!cancelled) setState({ status: "empty" });
          return;
        }
        const round = mostRecent(rounds);
        const analytics = await getRoundAnalytics(round.id);
        if (!cancelled) setState({ status: "ready", round, analytics });
      } catch (error) {
        if (!cancelled) {
          setState({
            status: "error",
            message: error instanceof Error ? error.message : "Failed to load dashboard data",
          });
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [userId, refreshKey]);

  const refresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  return { state, refresh };
}
