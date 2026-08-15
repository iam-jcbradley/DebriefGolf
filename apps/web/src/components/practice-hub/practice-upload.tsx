"use client";

import { type ChangeEvent, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Overline } from "@/components/ui/overline";
import { ApiError, uploadPracticeSession, type PracticeUploadResult } from "@/lib/api";

type UploadState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "success"; result: PracticeUploadResult }
  | { status: "error"; message: string };

const SOURCES = ["R10", "R50"] as const;

export interface PracticeUploadProps {
  userId: number | null;
  onUploaded?: (result: PracticeUploadResult) => void;
}

/** Upload an R10/R50 CSV/JSON export (PRD §6.1) — parsed server-side by
 * `app.services.parsers.launch_monitor_parser`. Per-row parse errors are
 * reported alongside a successful upload rather than blocking it, matching
 * the parser's own tolerance for a partially-malformed file. */
export function PracticeUpload({ userId, onUploaded }: PracticeUploadProps) {
  const [source, setSource] = useState<(typeof SOURCES)[number]>("R10");
  const [state, setState] = useState<UploadState>({ status: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (userId === null) {
      setState({ status: "error", message: "Enter a user ID before uploading." });
      return;
    }
    setState({ status: "uploading" });
    try {
      const result = await uploadPracticeSession(userId, source, file);
      setState({ status: "success", result });
      onUploaded?.(result);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Upload failed.";
      setState({ status: "error", message });
    }
  }

  function onFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void handleFile(file);
    event.target.value = "";
  }

  return (
    <div>
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm" htmlFor="practice-upload-source">
          <Overline as="span">Device</Overline>
          <select
            id="practice-upload-source"
            value={source}
            onChange={(event) => setSource(event.target.value as (typeof SOURCES)[number])}
            className="border-0 border-b border-border bg-transparent py-1 text-sm outline-none focus-visible:border-primary"
          >
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <Button
          type="button"
          variant="outline"
          onClick={() => inputRef.current?.click()}
          disabled={state.status === "uploading"}
        >
          Upload session file
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.json"
          className="hidden"
          aria-label="Upload R10/R50 session export"
          onChange={onFileInputChange}
        />
      </div>

      {state.status === "uploading" && (
        <p className="mt-3 text-sm text-muted-foreground">Uploading…</p>
      )}
      {state.status === "success" && (
        <div className="mt-3 text-sm" role="status">
          <p>
            Session logged — <strong>{state.result.shot_count}</strong> shots parsed.
          </p>
          {state.result.errors.length > 0 && (
            <p className="mt-1 text-muted-foreground">
              {state.result.errors.length} row(s) couldn&apos;t be parsed.
            </p>
          )}
        </div>
      )}
      {state.status === "error" && (
        <p className="mt-3 text-sm text-destructive" role="alert">
          {state.message}
        </p>
      )}
    </div>
  );
}
