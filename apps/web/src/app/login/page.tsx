"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { NavBar } from "@/components/nav-bar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Overline } from "@/components/ui/overline";
import { ApiError } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";

type Mode = "sign-in" | "create-account";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Set by CurrentUserProvider's unauthorized handler when a request 401s
  // out from under a session this tab thought was still good — see its
  // comment. Read once on mount's worth of params, not tied to `mode`, so
  // switching to "create account" and back doesn't make the notice reappear.
  const sessionExpired = searchParams.get("expired") === "1";
  const { user, signIn, signUp } = useCurrentUser();
  const [mode, setMode] = useState<Mode>("sign-in");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const creating = mode === "create-account";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (creating) {
        await signUp(name, email, password);
      } else {
        await signIn(email, password);
      }
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
          {creating ? "Open an account" : "Sign in"}
        </h1>

        {user ? (
          <Card className="mt-8">
            <CardHeader>
              <CardTitle className="text-lg">You&rsquo;re already signed in</CardTitle>
              <p className="text-sm text-muted-foreground">
                Signed in as <strong className="text-foreground">{user.name}</strong>.
              </p>
            </CardHeader>
            <CardContent>
              <Button type="button" onClick={() => router.push("/")}>
                Go to dashboard
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="mt-8">
            <CardContent className="pt-6">
              {sessionExpired && !creating && (
                <p className="mb-5 text-sm text-muted-foreground">Signed out — sign in again.</p>
              )}
              <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                {creating && (
                  <label className="flex flex-col gap-1 text-sm" htmlFor="name">
                    <Overline as="span">Name</Overline>
                    <Input
                      id="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      autoComplete="name"
                      required
                    />
                  </label>
                )}

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

                <div>
                  <label className="flex flex-col gap-1 text-sm" htmlFor="password">
                    <Overline as="span">Password</Overline>
                    <Input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete={creating ? "new-password" : "current-password"}
                      required
                    />
                  </label>
                  {creating ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      At least 10 characters. Length beats punctuation.
                    </p>
                  ) : (
                    <p className="mt-2 text-xs">
                      <Link
                        href="/forgot-password"
                        className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                      >
                        Forgot your password?
                      </Link>
                    </p>
                  )}
                </div>

                {error && (
                  <p className="text-sm text-destructive" role="alert">
                    {error}
                  </p>
                )}

                <Button type="submit" size="lg" disabled={submitting}>
                  {submitting
                    ? creating
                      ? "Creating account…"
                      : "Signing in…"
                    : creating
                      ? "Create account"
                      : "Sign in"}
                </Button>
              </form>

              <p className="mt-6 text-sm text-muted-foreground">
                {creating ? "Already have an account?" : "No account yet?"}{" "}
                <button
                  type="button"
                  className="text-primary underline-offset-4 hover:underline"
                  onClick={() => {
                    setMode(creating ? "sign-in" : "create-account");
                    setError(null);
                  }}
                >
                  {creating ? "Sign in" : "Create one"}
                </button>
              </p>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
