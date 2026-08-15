"use client";

import { useState } from "react";
import { NavBar } from "@/components/nav-bar";
import { SettingsTabs } from "@/components/settings/settings-tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Divider } from "@/components/ui/divider";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { ApiError, deleteUserData, getUserDataExport } from "@/lib/api";

type ExportState = "idle" | "working" | "error";
type DeleteState = "idle" | "confirming" | "working" | "done" | "error";

function DataExportPanel({ userId }: { userId: number | null }) {
  const [state, setState] = useState<ExportState>("idle");
  const [message, setMessage] = useState("");

  async function handleExport() {
    if (userId === null) {
      setState("error");
      setMessage("Enter a user ID first.");
      return;
    }
    setState("working");
    try {
      const data = await getUserDataExport(userId);
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

function DeleteAccountPanel({ userId }: { userId: number | null }) {
  const [state, setState] = useState<DeleteState>("idle");
  const [confirmText, setConfirmText] = useState("");
  const [message, setMessage] = useState("");

  async function handleDelete() {
    if (userId === null) return;
    setState("working");
    try {
      await deleteUserData(userId);
      setState("done");
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
        {state === "done" ? (
          <p className="text-sm" role="status">
            Your account and all associated data have been deleted.
          </p>
        ) : state === "confirming" || state === "working" ? (
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
          <Button
            type="button"
            variant="destructive"
            disabled={userId === null}
            onClick={() => setState("confirming")}
          >
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
  const [userIdInput, setUserIdInput] = useState("");
  const userId = userIdInput.trim() === "" ? null : Number(userIdInput);
  const validUserId = userId !== null && !Number.isNaN(userId) ? userId : null;

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <Overline accent>Settings</Overline>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight md:text-4xl">
          Privacy &amp; Data
        </h1>
        <SettingsTabs />

        <label className="mb-6 flex max-w-40 flex-col gap-1 text-sm" htmlFor="privacy-user-id">
          <Overline as="span">User ID</Overline>
          <Input
            id="privacy-user-id"
            type="number"
            min={1}
            value={userIdInput}
            onChange={(event) => setUserIdInput(event.target.value)}
          />
        </label>

        <div className="space-y-6">
          <DataExportPanel userId={validUserId} />
          <DeleteAccountPanel userId={validUserId} />
        </div>

        <Divider />

        <PrivacyNotice />
      </main>
    </div>
  );
}
