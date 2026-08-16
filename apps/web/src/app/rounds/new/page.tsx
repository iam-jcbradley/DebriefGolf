"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { NavBar } from "@/components/nav-bar";
import { NoPlayerSelected } from "@/components/no-player-selected";
import { ApiError, createRound, getCourses, type CourseListItem } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";

function NewRoundForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialCourseId = searchParams.get("course_id") ?? "";
  const { user } = useCurrentUser();

  const [courses, setCourses] = useState<CourseListItem[] | null>(null);
  const [courseId, setCourseId] = useState(initialCourseId);
  const [playedAt, setPlayedAt] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCourses()
      .then((result) => {
        if (!cancelled) setCourses(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load courses");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!user) return;
    const course = Number(courseId);
    if (!courseId || Number.isNaN(course)) {
      setError("Choose a course.");
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const round = await createRound({
        user_id: user.id,
        course_id: course,
        played_at: playedAt ? new Date(playedAt).toISOString() : undefined,
      });
      router.push(`/rounds/${round.id}/enter`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create round");
    } finally {
      setCreating(false);
    }
  }

  if (!user) {
    return (
      <main className="mx-auto max-w-md px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">New round</h1>
        <div className="mt-6">
          <NoPlayerSelected description="Choose a player before entering a round." />
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-md px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">New round</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Enter a round manually — the primary way to get round data in, since Garmin&apos;s
        developer API requires a paid account.
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        For <strong className="text-foreground">{user.name}</strong>.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-3">
        <label className="block text-sm">
          Course
          <select
            value={courseId}
            onChange={(e) => setCourseId(e.target.value)}
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          >
            <option value="">Select a course…</option>
            {courses?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
                {c.city ? ` — ${c.city}` : ""}
              </option>
            ))}
          </select>
        </label>
        <Link
          href="/courses/new"
          className="block text-xs text-muted-foreground underline hover:text-foreground"
        >
          Don&apos;t see your course? Add it
        </Link>

        <label className="block text-sm">
          Date played (optional)
          <input
            type="date"
            value={playedAt}
            onChange={(e) => setPlayedAt(e.target.value)}
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
        </label>

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={creating}
          className="rounded-md border bg-primary px-4 py-2 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {creating ? "Creating…" : "Create round"}
        </button>
      </form>
    </main>
  );
}

export default function NewRoundPage() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <Suspense fallback={null}>
        <NewRoundForm />
      </Suspense>
    </div>
  );
}
