"use client";

import { useEffect } from "react";
import { NavBar } from "@/components/nav-bar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";

/** Next's App Router error boundary for everything under the root layout —
 * a throw anywhere in a page or its children (a map component failing to
 * initialize, a render bug) lands here instead of the framework's default
 * whitescreen. Must be a Client Component; Next requires that. */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Card>
          <CardHeader>
            <Overline accent>Something went wrong</Overline>
            <CardTitle className="text-lg">This page hit an unexpected error</CardTitle>
            <p className="text-sm text-muted-foreground">
              Nothing you did caused this. Try again, or head back to the dashboard.
            </p>
          </CardHeader>
          <CardContent className="flex gap-3">
            <button
              type="button"
              onClick={reset}
              className="inline-flex h-10 items-center rounded-sm bg-primary px-5 text-sm text-primary-foreground transition-colors hover:bg-accent-hover"
            >
              Try again
            </button>
            {/* Plain <a>, not <Link>: a full navigation, not a client-side
                one, so whatever broke doesn't just break again on the way
                out. */}
            {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
            <a
              href="/"
              className="inline-flex h-10 items-center rounded-sm border border-border px-5 text-sm transition-colors hover:bg-muted"
            >
              Back to dashboard
            </a>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
