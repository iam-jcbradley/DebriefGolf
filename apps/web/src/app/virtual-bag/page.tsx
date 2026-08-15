"use client";

import { useState } from "react";
import { NavBar } from "@/components/nav-bar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Divider } from "@/components/ui/divider";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { VirtualRoundForm } from "@/components/virtual-bag/virtual-round-form";
import { VirtualRoundList } from "@/components/virtual-bag/virtual-round-list";
import { useVirtualRounds } from "@/lib/use-virtual-rounds";

export default function VirtualBagPage() {
  const [userIdInput, setUserIdInput] = useState("");
  const userId = userIdInput.trim() === "" ? null : Number(userIdInput);
  const validUserId = userId !== null && !Number.isNaN(userId) ? userId : null;

  const { state, refresh } = useVirtualRounds(validUserId);

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

        <Card className="mt-8">
          <CardHeader>
            <Overline>Log a sim round</Overline>
            <CardTitle className="text-lg">Home Tee Hero / E6 / GSPro</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              No login yet — enter the user ID this round belongs to.
            </p>
            <label className="mt-3 flex max-w-40 flex-col gap-1 text-sm" htmlFor="virtual-user-id">
              <Overline as="span">User ID</Overline>
              <Input
                id="virtual-user-id"
                type="number"
                min={1}
                value={userIdInput}
                onChange={(event) => setUserIdInput(event.target.value)}
              />
            </label>
            <div className="mt-4">
              <VirtualRoundForm userId={validUserId} onCreated={refresh} />
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
        {state.status === "idle" && (
          <p className="py-16 text-center text-muted-foreground">
            Enter a user ID above to see their sim rounds.
          </p>
        )}
      </main>
    </div>
  );
}
