"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { CombineCard } from "@/components/practice-hub/combine-card";
import { DeliveryProfileTable } from "@/components/practice-hub/delivery-profile-table";
import { PracticeUpload } from "@/components/practice-hub/practice-upload";
import { SimVsRealTable } from "@/components/practice-hub/sim-vs-real-table";
import { NavBar } from "@/components/nav-bar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Divider } from "@/components/ui/divider";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { cn } from "@/lib/utils";
import { usePracticeData } from "@/lib/use-practice-data";

// recharts is a ~100kB dependency (see docs/DEVELOPMENT_PLAN.md's Mapbox
// discipline note in Phase 4/5) — dynamically imported so a Practice Hub
// visit with no trend data yet doesn't pay for it.
const DeliveryTrendChart = dynamic(
  () => import("@/components/practice-hub/delivery-trend-chart").then((m) => m.DeliveryTrendChart),
  { ssr: false }
);

export default function PracticePage() {
  const [userIdInput, setUserIdInput] = useState("");
  const userId = userIdInput.trim() === "" ? null : Number(userIdInput);
  const validUserId = userId !== null && !Number.isNaN(userId) ? userId : null;

  const { state, refresh } = usePracticeData(validUserId);
  const [selectedClub, setSelectedClub] = useState<string | null>(null);

  const clubsWithTrend = state.status === "ready" ? Object.keys(state.delivery.trend) : [];
  const activeClub = selectedClub ?? clubsWithTrend[0] ?? null;

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Overline accent>Practice (R10/R50)</Overline>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight md:text-4xl">
          Practice Hub
        </h1>

        <Card className="mt-8">
          <CardHeader>
            <Overline>Log a session</Overline>
            <CardTitle className="text-lg">Bring in an R10/R50 export</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              No login yet — enter the user ID this session belongs to.
            </p>
            <label className="mt-3 flex max-w-40 flex-col gap-1 text-sm" htmlFor="practice-user-id">
              <Overline as="span">User ID</Overline>
              <Input
                id="practice-user-id"
                type="number"
                min={1}
                value={userIdInput}
                onChange={(event) => setUserIdInput(event.target.value)}
              />
            </label>
            <div className="mt-4">
              <PracticeUpload userId={validUserId} onUploaded={refresh} />
            </div>
          </CardContent>
        </Card>

        {state.status === "loading" && (
          <p className="py-16 text-center text-muted-foreground">Loading practice data…</p>
        )}

        {state.status === "error" && (
          <p className="py-16 text-center text-destructive" role="alert">
            {state.message}
          </p>
        )}

        {state.status === "ready" && (
          <>
            <Divider />

            <section>
              <Overline>Prescriptive combines</Overline>
              <h2 className="mt-1 font-serif text-2xl font-medium tracking-tight">
                What to work on
              </h2>
              {state.combines.combines.length === 0 ? (
                <p className="mt-4 text-sm text-muted-foreground">
                  No weaknesses detected from the data on file yet — keep logging rounds and
                  practice sessions.
                </p>
              ) : (
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  {state.combines.combines.map((combine, i) => (
                    <CombineCard
                      key={combine.weakness}
                      combine={combine}
                      signal={state.combines.weaknesses[i]}
                    />
                  ))}
                </div>
              )}
            </section>

            <Divider />

            <section>
              <DeliveryProfileTable clubs={state.delivery.clubs} />
            </section>

            {clubsWithTrend.length > 0 && (
              <section className="mt-6">
                <Card>
                  <CardHeader>
                    <Overline>Trend</Overline>
                    <CardTitle className="text-lg">Smash Factor Over Sessions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1">
                      {clubsWithTrend.map((club) => (
                        <button
                          key={club}
                          type="button"
                          onClick={() => setSelectedClub(club)}
                          aria-current={activeClub === club}
                          className={cn(
                            "rounded-md border px-2.5 py-1 text-sm",
                            activeClub === club
                              ? "border-primary bg-primary text-primary-foreground"
                              : "hover:bg-muted"
                          )}
                        >
                          {club}
                        </button>
                      ))}
                    </div>
                    <div className="mt-4">
                      {activeClub && (
                        <DeliveryTrendChart
                          club={activeClub}
                          points={state.delivery.trend[activeClub]}
                        />
                      )}
                    </div>
                  </CardContent>
                </Card>
              </section>
            )}

            <section className="mt-6">
              <SimVsRealTable rows={state.delivery.sim_vs_real_gapping} />
            </section>
          </>
        )}
      </main>
    </div>
  );
}
