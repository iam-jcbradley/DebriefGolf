import Link from "next/link";
import { NavBar } from "@/components/nav-bar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";

/** Replaces Next's unstyled default 404 for a route that doesn't exist —
 * distinct from a round/course/etc. that doesn't exist, which each page
 * already renders its own state for from a 404 API response. */
export default function NotFound() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Card>
          <CardHeader>
            <Overline accent>404</Overline>
            <CardTitle className="text-lg">This page doesn&apos;t exist</CardTitle>
            <p className="text-sm text-muted-foreground">
              Check the address, or head back to the dashboard.
            </p>
          </CardHeader>
          <CardContent>
            <Link
              href="/"
              className="inline-flex h-10 items-center rounded-sm bg-primary px-5 text-sm text-primary-foreground transition-colors hover:bg-accent-hover"
            >
              Back to dashboard
            </Link>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
