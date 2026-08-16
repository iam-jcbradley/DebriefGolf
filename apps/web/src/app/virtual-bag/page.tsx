"use client";

import { NavBar } from "@/components/nav-bar";
import { SignedOut } from "@/components/signed-out";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Divider } from "@/components/ui/divider";
import { Overline } from "@/components/ui/overline";
import { VirtualRoundForm } from "@/components/virtual-bag/virtual-round-form";
import { VirtualRoundList } from "@/components/virtual-bag/virtual-round-list";
import { useCurrentUser } from "@/lib/current-user";
import { useVirtualRounds } from "@/lib/use-virtual-rounds";

export default function VirtualBagPage() {
  const { user } = useCurrentUser();
  const { state, refresh } = useVirtualRounds(user?.id ?? null);

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <Overline accent>Virtual Bag</Overline>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight md:text-4xl">
          Sim Round Hub
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Home Tee Hero, E6, GSPro — logged separately, and never counted toward your real-world
          handicap.
        </p>

        {!user ? (
          <div className="mt-8">
            <SignedOut description="Sign in to log and view your sim rounds." />
          </div>
        ) : (
          <>
            <Card className="mt-8">
              <CardHeader>
                <Overline>Log a sim round</Overline>
                <CardTitle className="text-lg">Home Tee Hero / E6 / GSPro</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Logging for <strong className="text-foreground">{user.name}</strong>.
                </p>
                <div className="mt-4">
                  <VirtualRoundForm onCreated={refresh} />
                </div>
              </CardContent>
            </Card>

            <Divider />

            {state.status === "loading" && (
              <p className="py-16 text-center text-muted-foreground">Loading virtual rounds…</p>
            )}
            {state.status === "error" && (
              <p className="py-16 text-center text-destructive" role="alert">
                {state.message}
              </p>
            )}
            {state.status === "ready" && <VirtualRoundList rounds={state.rounds} />}
          </>
        )}
      </main>
    </div>
  );
}
