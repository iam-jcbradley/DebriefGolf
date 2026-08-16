"use client";

import { type ChangeEvent, type DragEvent, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError, uploadFitFile, type FitUploadResult } from "@/lib/api";
import { cn } from "@/lib/utils";

type UploadState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "success"; result: FitUploadResult }
  | { status: "error"; message: string };

export interface FitUploadProps {
  onUploaded?: (result: FitUploadResult) => void;
}

/** The round is attributed to the session user server-side — this component
 * has no say in whose round it is, which is why it takes no user id. */
export function FitUpload({ onUploaded }: FitUploadProps) {
  const [state, setState] = useState<UploadState>({ status: "idle" });
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setState({ status: "uploading" });
    try {
      const result = await uploadFitFile(file);
      setState({ status: "success", result });
      onUploaded?.(result);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Upload failed.";
      setState({ status: "error", message });
    }
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) void handleFile(file);
  }

  function onFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void handleFile(file);
    event.target.value = "";
  }

  return (
    <div
      data-testid="fit-upload-dropzone"
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      className={cn(
        "rounded-lg border-2 border-dashed p-6 text-center transition-colors",
        isDragging ? "border-primary bg-accent" : "border-border"
      )}
    >
      <p className="text-sm text-muted-foreground">
        Drag and drop a Garmin <code>.fit</code> activity file here, or
      </p>
      <Button
        type="button"
        variant="outline"
        className="mt-2"
        onClick={() => inputRef.current?.click()}
        disabled={state.status === "uploading"}
      >
        Choose file
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept=".fit"
        className="hidden"
        aria-label="Upload .FIT file"
        onChange={onFileInputChange}
      />

      {state.status === "uploading" && (
        <p className="mt-3 text-sm text-muted-foreground">Uploading…</p>
      )}
      {state.status === "success" && (
        <p className="mt-3 text-sm" role="status">
          Round uploaded — status: <strong>{state.result.status.replace("_", " ")}</strong>
          {state.result.point_count > 0 && ` (${state.result.point_count} GPS points)`}
        </p>
      )}
      {state.status === "error" && (
        <p className="mt-3 text-sm text-destructive" role="alert">
          {state.message}
        </p>
      )}
    </div>
  );
}
