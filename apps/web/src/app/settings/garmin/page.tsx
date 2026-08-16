"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { NavBar } from "@/components/nav-bar";
import { NoPlayerSelected } from "@/components/no-player-selected";
import { SettingsTabs } from "@/components/settings/settings-tabs";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  disconnectGarmin,
  getGarminStatus,
  startGarminAuthorize,
} from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";

function CallbackBanner() {
  const searchParams = useSearchParams();
  const connected = searchParams.get("connected") === "1";
  const error = searchParams.get("error");

  if (connected) {
    return (
      <p className="mb-4 rounded-md border border-delta-good-text/30 bg-delta-good-text/10 p-3 text-sm text-delta-good-text" role="status">
        Garmin account connected.
      </p>
    );
  }
  if (error) {
    return (
      <p className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive" role="alert">
        Couldn&apos;t connect Garmin: {error}
      </p>
    );
  }
  return null;
}

function GarminConnectPanel({ userId, playerName }: { userId: number; playerName: string }) {
  const [status, setStatus] = useState<"unknown" | "connected" | "not_connected">("unknown");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getGarminStatus(userId)
      .then((result) => {
        if (!cancelled) setStatus(result.connected ? "connected" : "not_connected");
      })
      .catch(() => {
        if (!cancelled) setStatus("unknown");
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  async function handleConnect() {
    setBusy(true);
    setMessage(null);
    try {
      const { authorize_url } = await startGarminAuthorize(userId);
      window.location.href = authorize_url;
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Could not start the Garmin connection.");
      setBusy(false);
    }
  }

  async function handleDisconnect() {
    setBusy(true);
    setMessage(null);
    try {
      await disconnectGarmin(userId);
      setStatus("not_connected");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Could not disconnect Garmin.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border p-4">
      <h2 className="text-lg font-semibold">Garmin Connect</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Link your Garmin Connect account for automatic round sync (PRD §4.1), for{" "}
        <strong className="text-foreground">{playerName}</strong>.
      </p>

      <p className="mt-3 text-sm text-muted-foreground">
        Status:{" "}
        <span className="font-medium text-foreground">
          {status === "connected" ? "Connected" : status === "not_connected" ? "Not connected" : "—"}
        </span>
      </p>

      <div className="mt-3 flex gap-2">
        <Button type="button" onClick={handleConnect} disabled={busy}>
          Connect Garmin
        </Button>
        {status === "connected" && (
          <Button type="button" variant="outline" onClick={handleDisconnect} disabled={busy}>
            Disconnect
          </Button>
        )}
      </div>

      {message && (
        <p className="mt-3 text-sm text-destructive" role="alert">
          {message}
        </p>
      )}
    </section>
  );
}

export default function GarminSettingsPage() {
  const { user } = useCurrentUser();

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <SettingsTabs />
        <Suspense fallback={null}>
          <CallbackBanner />
        </Suspense>
        {user ? (
          <GarminConnectPanel userId={user.id} playerName={user.name} />
        ) : (
          <NoPlayerSelected description="Choose a player to manage their Garmin connection." />
        )}
      </main>
    </div>
  );
}
