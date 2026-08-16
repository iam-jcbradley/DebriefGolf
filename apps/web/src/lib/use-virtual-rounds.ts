"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, getVirtualRounds, type VirtualRound } from "@/lib/api";

export type VirtualRoundsState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; rounds: VirtualRound[] };

export interface UseVirtualRounds {
  state: VirtualRoundsState;
  refresh: () => void;
}

export function useVirtualRounds(signedIn: boolean): UseVirtualRounds {
  const [state, setState] = useState<VirtualRoundsState>({ status: "idle" });
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
        const rounds = await getVirtualRounds();
        if (!cancelled) setState({ status: "ready", rounds });
      } catch (error) {
        if (!cancelled) {
          setState({
            status: "error",
            message: error instanceof ApiError ? error.message : "Failed to load virtual rounds",
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
