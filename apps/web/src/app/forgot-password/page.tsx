"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { NavBar } from "@/components/nav-bar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { ApiError, requestPasswordReset } from "@/lib/api";

/**
 * Request step of Phase 15's password reset. The response is the same
 * "check your email" line whether or not the address has an account —
 * matching `POST /auth/forgot-password`'s deliberately identical answer
 * either way (see the route's docstring) — so this page has no branch for
 * "no such account" to accidentally show.
 */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await requestPasswordReset({ email });
      setSent(true);
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
          Reset your password
        </h1>

        <Card className="mt-8">
          <CardContent className="pt-6">
            {sent ? (
              <p className="text-sm text-muted-foreground">
                Check your email for a reset link. It expires in an hour.
              </p>
            ) : (
              <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                <label className="flex flex-col gap-1 text-sm" htmlFor="email">
                  <Overline as="span">Email</Overline>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                  />
                </label>

                {error && (
                  <p className="text-sm text-destructive" role="alert">
                    {error}
                  </p>
                )}

                <Button type="submit" size="lg" disabled={submitting}>
                  {submitting ? "Sending…" : "Send reset link"}
                </Button>
              </form>
            )}

            <p className="mt-6 text-sm text-muted-foreground">
              <Link href="/login" className="text-primary underline-offset-4 hover:underline">
                Back to sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
