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

/** `signedIn`: whether there's a session to fetch for. The API scopes
 * rounds to the session user, so there is no id to pass — and no way for
 * the dashboard to ask for anyone else's round even by accident. */
export function useDashboardData(signedIn: boolean): UseDashboardData {
  const [state, setState] = useState<DashboardState>({ status: "idle" });
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!signedIn) {
      setState({ status: "idle" });
      return;
    }
    let cancelled = false;

    async function load() {
      setState({ status: "loading" });
      try {
        // Ask for one round rather than fetching every round the player has
        // ever played and sorting client-side: the API returns them newest
        // first, so the newest is the only one this page needs.
        const rounds = await getRounds({ limit: 1 });
        if (rounds.length === 0) {
          if (!cancelled) setState({ status: "empty" });
          return;
        }
        const round = rounds[0];
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
  }, [signedIn, refreshKey]);

  const refresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  return { state, refresh };
}
