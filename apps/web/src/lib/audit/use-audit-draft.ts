"use client";

import { useEffect, useRef, useState } from "react";
import { clearDraft, loadDraft, saveDraft } from "@/lib/audit/draft-store";
import type { DraftShot } from "@/lib/audit/types";

export interface UseAuditDraft {
  shots: DraftShot[];
  setShots: (shots: DraftShot[]) => void;
  loaded: boolean;
  clear: () => Promise<void>;
}

/** Hydrates a round's draft shots from IndexedDB on mount (falling back to
 * `initialShots` if there's no saved draft yet), then persists every
 * subsequent change. */
export function useAuditDraft(roundId: number, initialShots: DraftShot[]): UseAuditDraft {
  const [shots, setShots] = useState<DraftShot[]>(initialShots);
  const [loaded, setLoaded] = useState(false);
  const hydrating = useRef(true);

  useEffect(() => {
    let cancelled = false;
    hydrating.current = true;
    loadDraft(roundId)
      .then((draft) => {
        if (cancelled) return;
        if (draft) setShots(draft.shots);
        setLoaded(true);
      })
      .finally(() => {
        hydrating.current = false;
      });
    return () => {
      cancelled = true;
    };
    // `initialShots` is intentionally excluded: it's only a seed for the
    // very first render, not a reactive dependency to re-hydrate on.
  }, [roundId]);

  useEffect(() => {
    if (hydrating.current) return;
    void saveDraft(roundId, shots);
  }, [roundId, shots]);

  async function clear() {
    await clearDraft(roundId);
  }

  return { shots, setShots, loaded, clear };
}
