"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { HoleGeometryEditor, type HoleGeometryValue } from "@/components/course-builder/hole-geometry-editor";
import { NavBar } from "@/components/nav-bar";
import {
  ApiError,
  createCourse,
  getOsmCourseGeometry,
  searchOsmCourses,
  type CourseDetail,
  type LatLngPoint,
  type OsmCourseSummary,
} from "@/lib/api";
import { localYards } from "@/lib/hole-replay/projection";
import { cn } from "@/lib/utils";

// No better default available without a real location signal — same
// fallback the seed data uses (app/db/seed.py's BASE_LAT/BASE_LNG).
const DEFAULT_CENTER: LatLngPoint = { lat: 33.7, lng: -78.9 };

interface HoleDraft {
  number: number;
  par: number;
  yardage: number | null;
  tee_location: LatLngPoint | null;
  green_center: LatLngPoint | null;
  green_boundary: LatLngPoint[] | null;
}

function distanceYards(a: LatLngPoint, b: LatLngPoint): number {
  const { east, north } = localYards(a, b);
  return Math.round(Math.hypot(east, north));
}

function nextHoleNumber(holes: HoleDraft[]): number {
  return holes.length === 0 ? 1 : Math.max(...holes.map((h) => h.number)) + 1;
}

export default function NewCoursePage() {
  const [step, setStep] = useState<"search" | "build">("search");

  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<OsmCourseSummary[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [osmRelationId, setOsmRelationId] = useState<number | null>(null);
  const [center, setCenter] = useState<LatLngPoint>(DEFAULT_CENTER);
  const [holes, setHoles] = useState<HoleDraft[]>([]);
  const [editingHoleNumber, setEditingHoleNumber] = useState<number | null>(null);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedCourse, setSavedCourse] = useState<CourseDetail | null>(null);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearchError(null);
    try {
      setSearchResults(await searchOsmCourses(query.trim()));
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.message : "Search failed");
      setSearchResults(null);
    } finally {
      setSearching(false);
    }
  }

  async function handleUseOsmResult(result: OsmCourseSummary) {
    setSearchError(null);
    try {
      const draft = await getOsmCourseGeometry(result.osm_type, result.osm_id);
      setName(draft.name || result.name);
      setCity(draft.city ?? result.city ?? "");
      setState(draft.state ?? result.state ?? "");
      setOsmRelationId(draft.osm_relation_id);
      setCenter(result.center ?? draft.holes.find((h) => h.tee_location)?.tee_location ?? DEFAULT_CENTER);
      setHoles(
        draft.holes.map((h, i) => ({
          number: h.number ?? i + 1,
          par: h.par ?? 4,
          yardage: h.yardage,
          tee_location: h.tee_location,
          green_center: h.green_center,
          green_boundary: h.green_boundary,
        }))
      );
      setStep("build");
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.message : "Failed to fetch course geometry");
    }
  }

  function handleStartFromScratch() {
    setName(query.trim());
    setCity("");
    setState("");
    setOsmRelationId(null);
    setHoles([]);
    setCenter(DEFAULT_CENTER);
    setStep("build");
    if (typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setCenter({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => {
          // denied or unavailable — keep DEFAULT_CENTER, the user can still
          // place every point by hand
        },
        { timeout: 5000 }
      );
    }
  }

  function addHole() {
    setHoles([
      ...holes,
      {
        number: nextHoleNumber(holes),
        par: 4,
        yardage: null,
        tee_location: null,
        green_center: null,
        green_boundary: null,
      },
    ]);
  }

  function updateHole(index: number, patch: Partial<HoleDraft>) {
    setHoles((prev) => prev.map((h, i) => (i === index ? { ...h, ...patch } : h)));
  }

  function handleGeometryChange(index: number, geometry: HoleGeometryValue) {
    setHoles((prev) =>
      prev.map((h, i) => {
        if (i !== index) return h;
        const updated = { ...h, ...geometry };
        if (updated.tee_location && updated.green_center && updated.yardage == null) {
          updated.yardage = distanceYards(updated.tee_location, updated.green_center);
        }
        return updated;
      })
    );
  }

  function removeHole(index: number) {
    const removedNumber = holes[index].number;
    setHoles((prev) => prev.filter((_, i) => i !== index));
    if (editingHoleNumber === removedNumber) setEditingHoleNumber(null);
  }

  const holeNumbers = holes.map((h) => h.number);
  const hasDuplicateNumbers = new Set(holeNumbers).size !== holeNumbers.length;
  const incompleteHoles = holes.filter((h) => h.yardage == null);
  const canSave =
    name.trim().length > 0 && holes.length > 0 && !hasDuplicateNumbers && incompleteHoles.length === 0;

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      const created = await createCourse({
        name: name.trim(),
        city: city.trim() || null,
        state: state.trim() || null,
        osm_relation_id: osmRelationId,
        holes: holes.map((h) => ({
          number: h.number,
          par: h.par,
          yardage: h.yardage as number,
          tee_location: h.tee_location,
          green_center: h.green_center,
          green_boundary: h.green_boundary,
        })),
      });
      setSavedCourse(created);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Failed to save course");
    } finally {
      setSaving(false);
    }
  }

  if (savedCourse) {
    return (
      <div className="min-h-screen">
        <NavBar />
        <main className="mx-auto max-w-2xl px-6 py-10">
          <h1 className="text-2xl font-semibold tracking-tight">Course saved</h1>
          <p className="mt-2 text-muted-foreground">
            {savedCourse.name} — {savedCourse.holes.length}{" "}
            {savedCourse.holes.length === 1 ? "hole" : "holes"}.
          </p>
          <Link
            href={`/rounds/new?course_id=${savedCourse.id}`}
            className="mt-6 inline-block rounded-md border px-4 py-2 text-sm hover:bg-muted"
          >
            Create a round for this course
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Add a course</h1>

        {step === "search" && (
          <div className="mt-6 space-y-4">
            <form onSubmit={handleSearch} className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search OpenStreetMap by course name"
                className="flex-1 rounded-md border px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={searching || !query.trim()}
                className="rounded-md border px-4 py-2 text-sm hover:bg-muted disabled:opacity-50"
              >
                {searching ? "Searching…" : "Search"}
              </button>
            </form>

            {searchError && (
              <p role="alert" className="text-sm text-destructive">
                {searchError}
              </p>
            )}

            {searchResults && searchResults.length === 0 && (
              <p className="text-sm text-muted-foreground">No matches on OpenStreetMap.</p>
            )}

            {searchResults && searchResults.length > 0 && (
              <ul className="space-y-2">
                {searchResults.map((result) => (
                  <li
                    key={`${result.osm_type}-${result.osm_id}`}
                    className="flex items-center justify-between rounded-md border px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-medium">{result.name}</p>
                      {(result.city || result.state) && (
                        <p className="text-xs text-muted-foreground">
                          {[result.city, result.state].filter(Boolean).join(", ")}
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleUseOsmResult(result)}
                      className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
                    >
                      Use this course
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <button
              type="button"
              onClick={handleStartFromScratch}
              className="text-sm text-muted-foreground underline hover:text-foreground"
            >
              Can&apos;t find it — start from scratch
            </button>
          </div>
        )}

        {step === "build" && (
          <div className="mt-6 space-y-6">
            <div className="space-y-2">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Course name"
                aria-label="Course name"
                className="w-full rounded-md border px-3 py-2 text-sm"
              />
              <div className="flex gap-2">
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="City"
                  aria-label="City"
                  className="flex-1 rounded-md border px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  placeholder="State"
                  aria-label="State"
                  className="w-24 rounded-md border px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="space-y-3">
              {holes.map((hole, index) => (
                <div key={hole.number} className="rounded-md border p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <label className="text-xs text-muted-foreground">
                      Hole
                      <input
                        type="number"
                        value={hole.number}
                        onChange={(e) => updateHole(index, { number: Number(e.target.value) })}
                        className="ml-1 w-14 rounded-md border px-2 py-1 text-sm"
                      />
                    </label>
                    <label className="text-xs text-muted-foreground">
                      Par
                      <select
                        value={hole.par}
                        onChange={(e) => updateHole(index, { par: Number(e.target.value) })}
                        className="ml-1 rounded-md border px-2 py-1 text-sm"
                      >
                        {[3, 4, 5].map((p) => (
                          <option key={p} value={p}>
                            {p}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-xs text-muted-foreground">
                      Yardage
                      <input
                        type="number"
                        value={hole.yardage ?? ""}
                        onChange={(e) =>
                          updateHole(index, {
                            yardage: e.target.value === "" ? null : Number(e.target.value),
                          })
                        }
                        className="ml-1 w-20 rounded-md border px-2 py-1 text-sm"
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() =>
                        setEditingHoleNumber(editingHoleNumber === hole.number ? null : hole.number)
                      }
                      className={cn(
                        "ml-auto rounded-md border px-2.5 py-1 text-sm",
                        editingHoleNumber === hole.number
                          ? "border-primary bg-primary text-primary-foreground"
                          : "hover:bg-muted"
                      )}
                    >
                      {hole.tee_location || hole.green_center ? "Edit geometry" : "Add geometry"}
                    </button>
                    <button
                      type="button"
                      onClick={() => removeHole(index)}
                      className="rounded-md border px-2.5 py-1 text-sm text-destructive hover:bg-muted"
                    >
                      Remove
                    </button>
                  </div>

                  {editingHoleNumber === hole.number && (
                    <div className="mt-3">
                      <HoleGeometryEditor
                        center={hole.tee_location ?? hole.green_center ?? center}
                        value={{
                          tee_location: hole.tee_location,
                          green_center: hole.green_center,
                          green_boundary: hole.green_boundary,
                        }}
                        onChange={(geometry) => handleGeometryChange(index, geometry)}
                      />
                    </div>
                  )}
                </div>
              ))}

              <button
                type="button"
                onClick={addHole}
                className="w-full rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground hover:bg-muted"
              >
                Add hole
              </button>
            </div>

            {hasDuplicateNumbers && (
              <p role="alert" className="text-sm text-destructive">
                Hole numbers must be unique.
              </p>
            )}
            {saveError && (
              <p role="alert" className="text-sm text-destructive">
                {saveError}
              </p>
            )}

            <button
              type="button"
              onClick={handleSave}
              disabled={!canSave || saving}
              className="rounded-md border bg-primary px-4 py-2 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save course"}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
