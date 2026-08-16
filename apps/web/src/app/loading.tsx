import { NavBar } from "@/components/nav-bar";

/** Shown during a route transition while the next segment's server-side
 * work resolves — the client-side data each page fetches after mount
 * (rounds, practice data, etc.) has its own "Loading…" state already and
 * isn't what this covers. */
export default function Loading() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <p className="py-24 text-center text-muted-foreground">Loading…</p>
      </main>
    </div>
  );
}
