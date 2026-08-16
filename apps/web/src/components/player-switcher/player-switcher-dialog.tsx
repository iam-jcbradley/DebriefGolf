"use client";

import { Dialog } from "@base-ui/react/dialog";
import { type FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { ApiError, createUser, searchUsers, type UserSummary } from "@/lib/api";
import type { CurrentUser } from "@/lib/current-user";

const SEARCH_DEBOUNCE_MS = 250;
const MIN_QUERY_LENGTH = 2;

type Step = "search" | "create";

export interface PlayerSwitcherDialogProps {
  open: boolean;
  currentUser: CurrentUser | null;
  onClose: () => void;
  onSelect: (user: CurrentUser) => void;
  onClear: () => void;
}

/** The "no login yet" identity picker (PRD's placeholder for real auth):
 * search for a player by name, or create a new one. Persisted client-side
 * by `CurrentUserProvider` (`src/lib/current-user.tsx`) so no page needs
 * its own numeric "User ID" input anymore. */
export function PlayerSwitcherDialog({
  open,
  currentUser,
  onClose,
  onSelect,
  onClear,
}: PlayerSwitcherDialogProps) {
  const [step, setStep] = useState<Step>("search");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSummary[]>([]);
  const [email, setEmail] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setStep("search");
    setQuery("");
    setResults([]);
    setEmail("");
    setError(null);
  }, [open]);

  useEffect(() => {
    if (step !== "search" || query.trim().length < MIN_QUERY_LENGTH) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const timeout = setTimeout(() => {
      searchUsers(query.trim())
        .then((found) => {
          if (!cancelled) setResults(found);
        })
        .catch(() => {
          if (!cancelled) setResults([]);
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [query, step]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    const name = query.trim();
    if (!name) return;
    setCreating(true);
    setError(null);
    try {
      const user = await createUser({ name, email: email.trim() });
      onSelect({ id: user.id, name: user.name });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create player.");
    } finally {
      setCreating(false);
    }
  }

  const trimmedQuery = query.trim();

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 bg-black/40" />
        <Dialog.Popup className="fixed top-1/2 left-1/2 w-96 -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-card p-4 shadow-lg">
          {step === "search" ? (
            <>
              <Dialog.Title className="font-serif text-lg font-medium">
                Who&apos;s playing?
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-muted-foreground">
                No login yet — type a name to find or create a player.
              </Dialog.Description>

              <label className="mt-4 flex flex-col gap-1 text-sm" htmlFor="player-search-query">
                <Overline as="span">Name</Overline>
                <Input
                  id="player-search-query"
                  autoFocus
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Jane Doe"
                />
              </label>

              {results.length > 0 && (
                <ul className="mt-3 max-h-48 divide-y divide-border overflow-y-auto rounded-md border border-border">
                  {results.map((result) => (
                    <li key={result.id}>
                      <button
                        type="button"
                        className="block w-full px-3 py-2 text-left text-sm hover:bg-muted"
                        onClick={() => onSelect(result)}
                      >
                        {result.name}
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {trimmedQuery.length >= MIN_QUERY_LENGTH && (
                <Button
                  type="button"
                  variant="outline"
                  className="mt-3 w-full"
                  onClick={() => setStep("create")}
                >
                  Create &quot;{trimmedQuery}&quot; as a new player
                </Button>
              )}

              {currentUser && (
                <button
                  type="button"
                  onClick={onClear}
                  className="mt-4 text-xs text-muted-foreground underline hover:text-foreground"
                >
                  Not {currentUser.name}? Clear saved player
                </button>
              )}
            </>
          ) : (
            <form onSubmit={handleCreate}>
              <Dialog.Title className="font-serif text-lg font-medium">
                New player: {trimmedQuery}
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-muted-foreground">
                An email keeps this player distinct from anyone else using the app.
              </Dialog.Description>

              <label className="mt-4 flex flex-col gap-1 text-sm" htmlFor="player-create-email">
                <Overline as="span">Email</Overline>
                <Input
                  id="player-create-email"
                  type="email"
                  required
                  autoFocus
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>

              {error && (
                <p className="mt-2 text-sm text-destructive" role="alert">
                  {error}
                </p>
              )}

              <div className="mt-4 flex gap-2">
                <Button type="submit" disabled={creating}>
                  {creating ? "Creating…" : "Create player"}
                </Button>
                <Button type="button" variant="ghost" onClick={() => setStep("search")}>
                  Back
                </Button>
              </div>
            </form>
          )}
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
