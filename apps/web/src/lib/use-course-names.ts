"use client";

import useSWR from "swr";
import { getCourses, type CourseListItem } from "@/lib/api";

/**
 * Resolves a round's `course_id` to a display name. `Round` carries only
 * the id, so any screen that wants to name the course a round was played
 * at needs this lookup — the dashboard and the rounds list both do, which
 * is why it lives here rather than being repeated in each.
 *
 * SWR dedupes the underlying `/api/courses` request across every caller,
 * so mounting this in several places on one page costs one fetch.
 */
export function useCourseNames() {
  const { data } = useSWR<CourseListItem[]>("courses", getCourses);

  /**
   * `undefined` means "not known yet" — either the round has no course, or
   * the course list hasn't arrived. Deliberately *not* a placeholder
   * string: returning `Course #12` while the list loads would flash a
   * database id on screen and then replace it with the real name a moment
   * later. Callers supply their own fallback with `??`.
   */
  function courseName(courseId: number | null): string | undefined {
    if (courseId === null || !data) return undefined;
    return data.find((c) => c.id === courseId)?.name ?? `Course #${courseId}`;
  }

  return { courseName, courses: data, loaded: data !== undefined };
}
