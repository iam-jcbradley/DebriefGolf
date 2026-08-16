"use client";

import useSWR from "swr";
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

/** `userId`: scopes the SWR cache key so switching who's signed in (no
 * forced page reload — see current-user.tsx) can't briefly render the
 * previous player's cached rounds before revalidating. `null` disables the
 * fetch entirely. */
export function useVirtualRounds(userId: number | null): UseVirtualRounds {
  const { data, error, isLoading, mutate } = useSWR(
    userId !== null ? ["virtual-rounds", userId] : null,
    () => getVirtualRounds()
  );

  let state: VirtualRoundsState;
  if (userId === null) {
    state = { status: "idle" };
  } else if (error) {
    state = {
      status: "error",
      message: error instanceof ApiError ? error.message : "Failed to load virtual rounds",
    };
  } else if (isLoading || !data) {
    state = { status: "loading" };
  } else {
    state = { status: "ready", rounds: data };
  }

  return { state, refresh: () => void mutate() };
}
