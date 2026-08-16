"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { NavBar } from "@/components/nav-bar";
import { SignedOut } from "@/components/signed-out";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";
import { ApiError, getRounds, type RoundStatus, type RoundSummary } from "@/lib/api";
import { useCourseNames } from "@/lib/use-course-names";
import { useCurrentUser } from "@/lib/current-user";

const PAGE_SIZE = 25;

const STATUS_LABELS: Record<RoundStatus, string> = {
  verified: "Verified",
  needs_audit: "Needs audit",
  casual_practice: "Casual practice",
};

const STATUS_CLASSES: Record<RoundStatus, string> = {
  verified: "text-status-good",
  needs_audit: "text-status-warning",
  casual_practice: "text-muted-foreground",
};

function roundHref(round: RoundSummary): string {
  return round.status === "needs_audit" ? `/rounds/${round.id}/audit` : `/rounds/${round.id}`;
}

export default function RoundsPage() {
  const { user, loading: userLoading } = useCurrentUser();

  const { courseName } = useCourseNames();

  const [rounds, setRounds] = useState<RoundSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    getRounds({ limit: PAGE_SIZE })
      .then((roundList) => {
        if (cancelled) return;
        setRounds(roundList);
        setHasMore(roundList.length === PAGE_SIZE);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load rounds");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user]);

  async function loadMore() {
    setLoadingMore(true);
    try {
      const next = await getRounds({ limit: PAGE_SIZE, offset: rounds.length });
      setRounds((prev) => [...prev, ...next]);
      setHasMore(next.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load more rounds");
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <Overline accent>Round Log</Overline>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight">Rounds</h1>

        {userLoading ? null : !user ? (
          <div className="mt-8">
            <SignedOut description="Sign in to see your rounds." />
          </div>
        ) : (
          <div className="mt-8">
            {error && (
              <p role="alert" className="text-destructive">
                {error}
              </p>
            )}

            {loading && <p className="py-16 text-center text-muted-foreground">Loading rounds…</p>}

            {!loading && !error && rounds.length === 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">No rounds logged yet</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Upload a `.FIT` file, or{" "}
                    <Link href="/rounds/new" className="underline hover:text-foreground">
                      enter one by hand
                    </Link>
                    , to see it here.
                  </p>
                </CardHeader>
              </Card>
            )}

            {!loading && rounds.length > 0 && (
              <Card>
                <CardContent className="p-0">
                  <ul className="divide-y divide-border">
                    {rounds.map((round) => (
                      <li key={round.id}>
                        <Link
                          href={roundHref(round)}
                          className="flex items-center justify-between gap-4 px-6 py-4 transition-colors hover:bg-secondary/40"
                        >
                          <div>
                            <p className="font-medium">
                              {round.course_id === null
                                ? "No course assigned"
                                : (courseName(round.course_id) ?? "—")}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {new Date(round.played_at).toLocaleDateString(undefined, {
                                year: "numeric",
                                month: "short",
                                day: "numeric",
                              })}{" "}
                              &middot;{" "}
                              <span className={STATUS_CLASSES[round.status]}>
                                {STATUS_LABELS[round.status]}
                              </span>
                            </p>
                          </div>
                          <p className="stat-numeral text-xl">{round.total_score ?? "—"}</p>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {!loading && hasMore && (
              <div className="mt-4 flex justify-center">
                <button
                  type="button"
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="kicker border-b border-transparent pb-0.5 text-muted-foreground transition-colors hover:border-primary hover:text-foreground disabled:opacity-50"
                >
                  {loadingMore ? "Loading…" : "Load more"}
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
