"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  type UserProfile,
} from "@/lib/api";

export interface CurrentUserContextValue {
  /** The signed-in player, or `null` when nobody is. */
  user: UserProfile | null;
  /** True only while the initial "who am I" request is in flight. */
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** Re-reads the session — for after a profile edit. */
  refresh: () => Promise<void>;
}

const CurrentUserContext = createContext<CurrentUserContextValue | null>(null);

/**
 * Identity is whatever the session cookie says (Phase 10). Before that this
 * provider kept a user id in localStorage, which was a *preference*, not an
 * identity — anyone could pick any player's name out of a search box and act
 * as them. Nothing here can name a user any more: the browser holds an
 * HttpOnly cookie that script can't read, and the server decides who that is.
 */
export function CurrentUserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setUser(await getCurrentUser());
    } catch (error) {
      // 401 is the ordinary "not signed in" answer, not a failure worth
      // surfacing. Anything else (API down, network) also leaves the app
      // signed out — there's no useful half-authenticated state.
      if (!(error instanceof ApiError)) {
        console.error("Failed to resolve the current session", error);
      }
      setUser(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void load().finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  const signIn = useCallback(async (email: string, password: string) => {
    setUser(await loginRequest({ email, password }));
  }, []);

  const signUp = useCallback(async (name: string, email: string, password: string) => {
    setUser(await registerRequest({ name, email, password }));
  }, []);

  const signOut = useCallback(async () => {
    try {
      await logoutRequest();
    } catch (error) {
      // Deliberately swallowed rather than rethrown. Signing out always
      // succeeds from the user's point of view: the local session is
      // dropped either way, and leaving the UI claiming someone is signed
      // in after they asked to leave is worse than a cookie that outlives
      // its TTL server-side. Rethrowing would also mean every caller needs
      // a try/catch around a click handler to avoid an unhandled rejection.
      console.error("Logout request failed; clearing the local session anyway", error);
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <CurrentUserContext.Provider
      value={{ user, loading, signIn, signUp, signOut, refresh: load }}
    >
      {children}
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
