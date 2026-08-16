"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { ApiError, getUserProfile } from "@/lib/api";
import { PlayerSwitcherDialog } from "@/components/player-switcher/player-switcher-dialog";

const STORAGE_KEY = "debrief-golf-current-user";

export interface CurrentUser {
  id: number;
  name: string;
}

export interface CurrentUserContextValue {
  /** `null` before the initial localStorage read resolves, and whenever
   * no player has been chosen yet. */
  user: CurrentUser | null;
  /** True only during the initial load (including the one-time
   * re-validation of a stored id against the backend) — not during
   * ordinary picker interactions. */
  loading: boolean;
  openPicker: () => void;
  clearUser: () => void;
}

const CurrentUserContext = createContext<CurrentUserContextValue | null>(null);

function readStoredUser(): CurrentUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      typeof (parsed as CurrentUser).id === "number" &&
      typeof (parsed as CurrentUser).name === "string"
    ) {
      return parsed as CurrentUser;
    }
    return null;
  } catch {
    return null;
  }
}

export function CurrentUserProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [pickerOpen, setPickerOpen] = useState(false);

  useEffect(() => {
    const stored = readStoredUser();
    if (!stored) {
      setLoading(false);
      return;
    }
    // Re-validate against the backend: the stored player may have deleted
    // their account (the /settings/privacy "delete my account" flow) since
    // this browser last used it, and silently acting as a user ID that no
    // longer exists is worse than asking again.
    let cancelled = false;
    getUserProfile(stored.id)
      .then((profile) => {
        if (!cancelled) setUserState({ id: profile.id, name: profile.name });
      })
      .catch((error) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 404) {
          window.localStorage.removeItem(STORAGE_KEY);
          setUserState(null);
        } else {
          // Network hiccup, not a real "this player is gone" signal —
          // keep the cached value rather than forcing a re-pick.
          setUserState(stored);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const setUser = useCallback((next: CurrentUser) => {
    setUserState(next);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, []);

  const clearUser = useCallback(() => {
    setUserState(null);
    window.localStorage.removeItem(STORAGE_KEY);
  }, []);

  const openPicker = useCallback(() => setPickerOpen(true), []);

  return (
    <CurrentUserContext.Provider value={{ user, loading, openPicker, clearUser }}>
      {children}
      <PlayerSwitcherDialog
        open={pickerOpen}
        currentUser={user}
        onClose={() => setPickerOpen(false)}
        onSelect={(picked) => {
          setUser(picked);
          setPickerOpen(false);
        }}
        onClear={() => {
          clearUser();
          setPickerOpen(false);
        }}
      />
    </CurrentUserContext.Provider>
  );
}

export function useCurrentUser(): CurrentUserContextValue {
  const ctx = useContext(CurrentUserContext);
  if (!ctx) {
    throw new Error("useCurrentUser must be used within a CurrentUserProvider");
  }
  return ctx;
}
