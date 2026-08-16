"use client";

import { useState } from "react";
import { NavBar } from "@/components/nav-bar";
import { SignedOut } from "@/components/signed-out";
import { SettingsTabs } from "@/components/settings/settings-tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Divider } from "@/components/ui/divider";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { ApiError, deleteUserData, getUserDataExport } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";

type ExportState = "idle" | "working" | "error";
type DeleteState = "idle" | "confirming" | "working" | "error";

function DataExportPanel({ userId }: { userId: number }) {
  const [state, setState] = useState<ExportState>("idle");
  const [message, setMessage] = useState("");

  async function handleExport() {
    setState("working");
    try {
      const data = await getUserDataExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `debrief-golf-export-user-${userId}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setState("idle");
    } catch (error) {
      setState("error");
      setMessage(error instanceof ApiError ? error.message : "Failed to export data.");
    }
  }

  return (
    <Card>
      <CardHeader>
        <Overline>Access &amp; portability</Overline>
        <CardTitle className="text-lg">Download Your Data</CardTitle>
        <p className="text-sm text-muted-foreground">
          A JSON file with your rounds, shots, R10/R50 practice sessions, and virtual rounds —
          everything Debrief Golf has stored about you, except OAuth credentials.
        </p>
      </CardHeader>
      <CardContent>
        <Button type="button" variant="outline" onClick={() => void handleExport()} disabled={state === "working"}>
          {state === "working" ? "Preparing export…" : "Download my data"}
        </Button>
        {state === "error" && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {message}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function DeleteAccountPanel({ onDeleted }: { onDeleted: () => void }) {
  const [state, setState] = useState<DeleteState>("idle");
  const [confirmText, setConfirmText] = useState("");
  const [message, setMessage] = useState("");

  async function handleDelete() {
    setState("working");
    try {
      await deleteUserData();
      // The player whose data this was just IS the current player — the
      // parent swaps this whole panel out for a deletion confirmation and
      // clears the persisted selection, so there's no "done" state to show
      // here; this component simply stops being rendered.
      onDeleted();
    } catch (error) {
      setState("error");
      setMessage(error instanceof ApiError ? error.message : "Failed to delete account.");
    }
  }

  return (
    <Card>
      <CardHeader>
        <Overline accent>Irreversible</Overline>
        <CardTitle className="text-lg">Delete My Account</CardTitle>
        <p className="text-sm text-muted-foreground">
          Permanently deletes your rounds, shots, practice sessions, virtual rounds, and Garmin
          connection. This is a real deletion, not a deactivation — it cannot be undone.
        </p>
      </CardHeader>
      <CardContent>
        {state === "confirming" || state === "working" ? (
          <div>
            <label className="flex max-w-64 flex-col gap-1 text-sm" htmlFor="delete-confirm">
              <Overline as="span">
                Type DELETE to confirm
              </Overline>
              <Input
                id="delete-confirm"
                value={confirmText}
                disabled={state === "working"}
                onChange={(event) => setConfirmText(event.target.value)}
              />
            </label>
            <div className="mt-3 flex gap-2">
              <Button
                type="button"
                variant="destructive"
                disabled={confirmText !== "DELETE" || state === "working"}
                onClick={() => void handleDelete()}
              >
                {state === "working" ? "Deleting…" : "Permanently delete my account"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={state === "working"}
                onClick={() => {
                  setState("idle");
                  setConfirmText("");
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <Button type="button" variant="destructive" onClick={() => setState("confirming")}>
            Delete my account
          </Button>
        )}
        {state === "error" && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {message}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function PrivacyNotice() {
  return (
    <Card>
      <CardHeader>
        <Overline>Draft — pending legal review</Overline>
        <CardTitle className="text-lg">How Debrief Golf Handles Your Data</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <p>
          This notice describes our current data practices. It has not yet been reviewed by
          counsel and should not be treated as a final legal document — see{" "}
          <span className="font-mono text-xs">docs/DATA_PRIVACY.md</span> for the engineering
          checklist this page implements.
        </p>
        <p>
          <strong className="text-foreground">What we collect:</strong> your rounds and shot-level
          GPS locations, course/hole geometry you build or link, R10/R50 launch monitor data you
          upload, virtual round scorecards, and — if you connect it — your Garmin Connect OAuth
          tokens.
        </p>
        <p>
          <strong className="text-foreground">Why:</strong> this data is processed to provide the
          diagnostic features you use directly (Strokes Gained, dispersion maps, practice
          recommendations) — not for advertising or resale.
        </p>
        <p>
          <strong className="text-foreground">Retention:</strong> round, shot, and practice data
          is kept until you delete your account below. Garmin OAuth tokens are replaced on
          reconnection and removed immediately on disconnect.
        </p>
        <p>
          <strong className="text-foreground">Sharing:</strong> we do not sell your data. It is
          not shared with third parties beyond what&apos;s needed to run the service (e.g. your own
          Garmin connection, which you control).
        </p>
        <p>
          <strong className="text-foreground">Your rights:</strong> download a copy of your data
          at any time, or permanently delete your account, both below.
        </p>
      </CardContent>
    </Card>
  );
}

export default function PrivacySettingsPage() {
  const { user, signOut } = useCurrentUser();
  // Deliberately independent of `user`: signing out (once the account is
  // deleted) flips `user` to null immediately, which would otherwise swap
  // this section over to <SignedOut> before anyone could see the "your
  // account was deleted" confirmation. Bug found in Phase 8's live-browser
  // pass; the same trap applies to sessions.
  const [deletedPlayerName, setDeletedPlayerName] = useState<string | null>(null);

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <Overline accent>Settings</Overline>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight md:text-4xl">
          Privacy &amp; Data
        </h1>
        <SettingsTabs />

        <div className="mt-6 space-y-6">
          {deletedPlayerName ? (
            <Card>
              <CardContent>
                <p className="text-sm" role="status">
                  {deletedPlayerName}&apos;s account and all associated data have been deleted.
                </p>
              </CardContent>
            </Card>
          ) : user ? (
            <>
              <p className="text-sm text-muted-foreground">
                Managing data for <strong className="text-foreground">{user.name}</strong>.
              </p>
              <DataExportPanel userId={user.id} />
              <DeleteAccountPanel
                onDeleted={() => {
                  setDeletedPlayerName(user.name);
                  void signOut();
                }}
              />
            </>
          ) : (
            <SignedOut description="Sign in to manage your data." />
          )}
        </div>

        <Divider />

        <PrivacyNotice />
      </main>
    </div>
  );
}
