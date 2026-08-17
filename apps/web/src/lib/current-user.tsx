"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  setUnauthorizedHandler,
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
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  // Read inside the unauthorized handler without adding `user` to that
  // effect's deps — the handler is registered once, not re-registered on
  // every sign-in/out, and it needs the *current* value at the moment a
  // 401 arrives, not the value from whenever it was registered.
  const userRef = useRef(user);
  useEffect(() => {
    userRef.current = user;
  });

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

  useEffect(() => {
    // A 401 from any protected endpoint (not the exempt auth flows — see
    // apiFetch's own list) means the session cookie stopped working out
    // from under a request that assumed it was still good. Only worth
    // acting on if this tab actually thought someone was signed in:
    // otherwise every anonymous visitor's ordinary 401s on protected pages
    // would bounce them to /login on their very first click, which is not
    // "your session expired," it's just what "signed out" looks like.
    setUnauthorizedHandler(() => {
      if (userRef.current !== null) {
        setUser(null);
        router.push("/login?expired=1");
      }
    });
    return () => setUnauthorizedHandler(null);
  }, [router]);

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
