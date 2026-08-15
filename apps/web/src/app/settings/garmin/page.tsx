"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { NavBar } from "@/components/nav-bar";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  disconnectGarmin,
  getGarminStatus,
  startGarminAuthorize,
} from "@/lib/api";

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

function GarminConnectPanel() {
  const [userIdInput, setUserIdInput] = useState("");
  const [status, setStatus] = useState<"unknown" | "connected" | "not_connected">("unknown");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const userId = userIdInput.trim() === "" ? null : Number(userIdInput);
  const validUserId = userId !== null && !Number.isNaN(userId) ? userId : null;

  useEffect(() => {
    if (validUserId === null) {
      setStatus("unknown");
      return;
    }
    let cancelled = false;
    getGarminStatus(validUserId)
      .then((result) => {
        if (!cancelled) setStatus(result.connected ? "connected" : "not_connected");
      })
      .catch(() => {
        if (!cancelled) setStatus("unknown");
      });
    return () => {
      cancelled = true;
    };
  }, [validUserId]);

  async function handleConnect() {
    if (validUserId === null) return;
    setBusy(true);
    setMessage(null);
    try {
      const { authorize_url } = await startGarminAuthorize(validUserId);
      window.location.href = authorize_url;
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Could not start the Garmin connection.");
      setBusy(false);
    }
  }

  async function handleDisconnect() {
    if (validUserId === null) return;
    setBusy(true);
    setMessage(null);
    try {
      await disconnectGarmin(validUserId);
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
        Link your Garmin Connect account for automatic round sync (PRD §4.1). There&apos;s no
        login yet, so tell us which user ID this is for.
      </p>

      <label className="mt-3 flex items-center gap-2 text-sm" htmlFor="garmin-user-id">
        User ID
        <input
          id="garmin-user-id"
          type="number"
          min={1}
          value={userIdInput}
          onChange={(event) => setUserIdInput(event.target.value)}
          className="w-24 rounded-md border bg-background px-2 py-1"
        />
      </label>

      {validUserId !== null && (
        <p className="mt-3 text-sm text-muted-foreground">
          Status:{" "}
          <span className="font-medium text-foreground">
            {status === "connected" ? "Connected" : status === "not_connected" ? "Not connected" : "—"}
          </span>
        </p>
      )}

      <div className="mt-3 flex gap-2">
        <Button type="button" onClick={handleConnect} disabled={validUserId === null || busy}>
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
  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <Suspense fallback={null}>
          <CallbackBanner />
        </Suspense>
        <GarminConnectPanel />
      </main>
    </div>
  );
}
