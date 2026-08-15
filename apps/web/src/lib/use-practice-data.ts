"use client";

import { useCallback, useEffect, useState } from "react";
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

/** Loads the Practice Hub's two data sources — delivery profile (PRD §6.1)
 * and prescriptive combines (PRD §7.1) — together, since both key off the
 * same `userId` and the page renders them side by side. */
export function usePracticeData(userId: number | null): UsePracticeData {
  const [state, setState] = useState<PracticeDataState>({ status: "idle" });
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
        const [delivery, combines] = await Promise.all([
          getDeliveryProfile(userId as number),
          getPracticeCombines(userId as number),
        ]);
        if (!cancelled) setState({ status: "ready", delivery, combines });
      } catch (error) {
        if (!cancelled) {
          setState({
            status: "error",
            message: error instanceof ApiError ? error.message : "Failed to load practice data",
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
