"use client";

import Link from "next/link";
import { CoachBriefButton } from "@/components/coach-brief/coach-brief-button";
import { FitUpload } from "@/components/fit-upload";
import { NavBar } from "@/components/nav-bar";
import { SignedOut } from "@/components/signed-out";
import { RoundSnapshot } from "@/components/round-snapshot";
import { TigerFiveMeter } from "@/components/tiger-five-meter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Divider } from "@/components/ui/divider";
import { Overline } from "@/components/ui/overline";
import { isPendingAnalytics } from "@/lib/api";
import { useCourseNames } from "@/lib/use-course-names";
import { useCurrentUser } from "@/lib/current-user";
import { useDashboardData } from "@/lib/use-dashboard-data";

export default function DashboardPage() {
  const { user } = useCurrentUser();
  const { state, refresh } = useDashboardData(user?.id ?? null);
  const { courseName } = useCourseNames();

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Overline accent>Today&apos;s Debrief</Overline>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight md:text-4xl">
          Round Summary
        </h1>

        {!user ? (
          <div className="mt-8">
            <SignedOut description="Sign in to log and view your rounds." />
          </div>
        ) : (
          <>
            {state.status === "loading" && (
              <p className="py-24 text-center text-muted-foreground">Loading your round…</p>
            )}

            {state.status === "error" && (
              <p className="py-24 text-center text-destructive" role="alert">
                {state.message}
              </p>
            )}

            {state.status === "empty" && (
              <>
                <Divider />
                <div className="py-8 text-center">
                  <h2 className="font-serif text-2xl font-medium tracking-tight">
                    No rounds logged yet.
                  </h2>
                  <p className="mt-2 text-muted-foreground">
                    Upload a `.FIT` file, or enter one by hand, to see your first debrief.
                  </p>
                </div>
              </>
            )}

            {state.status === "ready" && isPendingAnalytics(state.analytics) && (
              <>
                <Divider />
                <div className="py-8 text-center">
                  <h2 className="font-serif text-2xl font-medium tracking-tight">
                    Round uploaded — audit needed
                  </h2>
                  <p className="mt-2 text-muted-foreground">
                    This round doesn&apos;t have any shots recorded yet. Run it through the audit
                    wizard to see your Round Snapshot.
                  </p>
                  <Link
                    href={`/rounds/${state.analytics.round_id}/audit`}
                    className="mt-4 inline-block text-sm underline hover:text-primary"
                  >
                    Open the audit wizard
                  </Link>
                </div>
              </>
            )}

            {state.status === "ready" && !isPendingAnalytics(state.analytics) && (
              <>
                <div className="mt-8 grid gap-6 md:grid-cols-2">
                  <RoundSnapshot
                    round={state.round}
                    analytics={state.analytics}
                    courseName={courseName(state.round.course_id) ?? "Round Snapshot"}
                    coursePar={state.coursePar}
                  />
                  <TigerFiveMeter tigerFive={state.analytics.tiger_five} />
                </div>
                <p className="mt-5 text-sm">
                  <Link
                    href={`/rounds/${state.round.id}`}
                    className="text-foreground underline hover:text-primary"
                  >
                    View hole-by-hole replay
                  </Link>
                </p>
                <div className="mt-4">
                  <CoachBriefButton round={state.round} analytics={state.analytics} />
                </div>
              </>
            )}

            {/* Ingestion sits below the debrief deliberately: the reason to
                open this page is the round you already played, not the next
                upload. */}
            <Divider />
            <Card>
              <CardHeader>
                <Overline>Log a round</Overline>
                <CardTitle className="text-lg">Bring in another round</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Logging for <strong className="text-foreground">{user.name}</strong>.{" "}
                  <Link href="/rounds/new" className="text-foreground underline hover:text-primary">
                    Enter one by hand
                  </Link>{" "}
                  — the primary way in, since Garmin&apos;s developer API requires a paid account —
                  or drop a `.FIT` file below.
                </p>
                <div className="mt-4">
                  <FitUpload onUploaded={refresh} />
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
