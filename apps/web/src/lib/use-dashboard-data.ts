"use client";

import { useCallback, useEffect, useState } from "react";
import { getRoundAnalytics, getRounds, type RoundAnalyticsResponse, type RoundSummary } from "@/lib/api";

export type DashboardState =
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

export function useDashboardData(): UseDashboardData {
  const [state, setState] = useState<DashboardState>({ status: "loading" });
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState({ status: "loading" });
      try {
        const rounds = await getRounds();
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
  }, [refreshKey]);

  const refresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  return { state, refresh };
}
