"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { NavBar } from "@/components/nav-bar";
import { SignedOut } from "@/components/signed-out";
import { SettingsTabs } from "@/components/settings/settings-tabs";
import { Button } from "@/components/ui/button";
import { Overline } from "@/components/ui/overline";
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

function GarminConnectPanel({ playerName }: { playerName: string }) {
  const [status, setStatus] = useState<"unknown" | "connected" | "not_connected">("unknown");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getGarminStatus()
      .then((result) => {
        if (!cancelled) setStatus(result.connected ? "connected" : "not_connected");
      })
      .catch(() => {
        if (!cancelled) setStatus("unknown");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleConnect() {
    setBusy(true);
    setMessage(null);
    try {
      const { authorize_url } = await startGarminAuthorize();
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
      await disconnectGarmin();
      setStatus("not_connected");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Could not disconnect Garmin.");
    } finally {
      setBusy(false);
    }
  }

  // No heading inside this panel: the page's own H1 already says "Garmin
  // Connect", and repeating it made two headings with identical text.
  return (
    <section className="rounded-md border border-border bg-card p-6">
      <p className="text-sm text-muted-foreground">
        Link your Garmin Connect account for automatic round sync, for{" "}
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
      <main className="mx-auto max-w-3xl px-6 py-10">
        <Overline accent>Settings</Overline>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight md:text-4xl">
          Garmin Connect
        </h1>
        <SettingsTabs />
        <Suspense fallback={null}>
          <CallbackBanner />
        </Suspense>
        {user ? (
          <GarminConnectPanel playerName={user.name} />
        ) : (
          <SignedOut description="Sign in to manage your Garmin connection." />
        )}
      </main>
    </div>
  );
}
