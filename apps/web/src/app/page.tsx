"use client";

import { useState } from "react";
import Link from "next/link";
import { FitUpload } from "@/components/fit-upload";
import { NavBar } from "@/components/nav-bar";
import { RoundSnapshot } from "@/components/round-snapshot";
import { TigerFiveMeter } from "@/components/tiger-five-meter";
import { isPendingAnalytics } from "@/lib/api";
import { useDashboardData } from "@/lib/use-dashboard-data";

export default function DashboardPage() {
  const { state, refresh } = useDashboardData();
  const [userIdInput, setUserIdInput] = useState("");
  const userId = userIdInput.trim() === "" ? null : Number(userIdInput);

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <section className="mb-8 rounded-xl border p-4">
          <h2 className="text-lg font-semibold">Upload a round</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            There&apos;s no login yet, so tell us which user ID to upload this round for.
          </p>
          <label className="mt-2 flex items-center gap-2 text-sm" htmlFor="upload-user-id">
            User ID
            <input
              id="upload-user-id"
              type="number"
              min={1}
              value={userIdInput}
              onChange={(event) => setUserIdInput(event.target.value)}
              className="w-24 rounded-md border bg-background px-2 py-1"
            />
          </label>
          <div className="mt-3">
            <FitUpload userId={userId !== null && !Number.isNaN(userId) ? userId : null} onUploaded={refresh} />
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Don&apos;t have a `.FIT` file handy?{" "}
            <Link href="/rounds/new" className="underline hover:text-foreground">
              Enter a round manually
            </Link>{" "}
            instead — this is the primary way to get round data in, since Garmin&apos;s
            developer API requires a paid account.
          </p>
        </section>

        {state.status === "loading" && (
          <p className="py-24 text-center text-muted-foreground">Loading your latest round…</p>
        )}

        {state.status === "error" && (
          <p className="py-24 text-center text-destructive" role="alert">
            {state.message}
          </p>
        )}

        {state.status === "empty" && (
          <div className="py-16 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">No rounds yet</h1>
            <p className="mt-2 text-muted-foreground">
              Upload a .FIT file from your Garmin device to get your first Round Snapshot.
            </p>
          </div>
        )}

        {state.status === "ready" && isPendingAnalytics(state.analytics) && (
          <div className="py-16 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">Round uploaded — audit needed</h1>
            <p className="mt-2 text-muted-foreground">
              This round doesn&apos;t have any shots recorded yet. Run it through the audit
              wizard to see your Round Snapshot.
            </p>
            <Link
              href={`/rounds/${state.analytics.round_id}/audit`}
              className="mt-4 inline-block underline hover:text-foreground"
            >
              Open the audit wizard
            </Link>
          </div>
        )}

        {state.status === "ready" && !isPendingAnalytics(state.analytics) && (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <RoundSnapshot round={state.round} analytics={state.analytics} />
              <TigerFiveMeter tigerFive={state.analytics.tiger_five} />
            </div>
            <p className="mt-4 text-sm">
              <Link
                href={`/rounds/${state.round.id}`}
                className="underline hover:text-foreground"
              >
                View hole-by-hole replay
              </Link>
            </p>
          </>
        )}
      </main>
    </div>
  );
}
