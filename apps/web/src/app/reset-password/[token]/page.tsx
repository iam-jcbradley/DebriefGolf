"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { NavBar } from "@/components/nav-bar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { ApiError, resetPassword } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";

/**
 * Consume step of Phase 15's password reset. `POST /auth/reset-password`
 * already signs the caller in on success (resetting a password is itself
 * proof of owning the account), so this just has to make the client side
 * catch up — `refresh()` re-reads the session the response cookie already
 * set, the same call a profile edit uses.
 */
export default function ResetPasswordPage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const { refresh } = useCurrentUser();
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await resetPassword({ token: params.token, password });
      await refresh();
      router.push("/");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Something went wrong. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-md px-6 py-16">
        <Overline accent>Members</Overline>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight md:text-4xl">
          Set a new password
        </h1>

        <Card className="mt-8">
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <div>
                <label className="flex flex-col gap-1 text-sm" htmlFor="password">
                  <Overline as="span">New password</Overline>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    required
                  />
                </label>
                <p className="mt-2 text-xs text-muted-foreground">
                  At least 10 characters. Length beats punctuation.
                </p>
              </div>

              {error && (
                <p className="text-sm text-destructive" role="alert">
                  {error}
                </p>
              )}

              <Button type="submit" size="lg" disabled={submitting}>
                {submitting ? "Saving…" : "Set new password"}
              </Button>
            </form>

            <p className="mt-6 text-sm text-muted-foreground">
              <Link
                href="/forgot-password"
                className="text-primary underline-offset-4 hover:underline"
              >
                Request a new link
              </Link>
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
