import type { Lie } from "@/lib/audit/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type RoundStatus = "verified" | "needs_audit" | "casual_practice";

export interface RoundSummary {
  id: number;
  played_at: string;
  total_score: number | null;
  course_id: number | null;
  user_id: number;
  status: RoundStatus;
}

export type SGCategory = "OTT" | "APP" | "ARG" | "PUTT";

export type ApproachLeave = "on_green" | "short_sided" | "safe_leave" | "unclassified";

export interface RoundAnalyticsPending {
  round_id: number;
  status: RoundStatus;
  needs_shots: true;
}

export interface RoundShotAnalytics {
  shot_id: number | null;
  category: SGCategory;
  strokes_gained: number;
  approach_leave: ApproachLeave;
}

export interface RoundAnalytics {
  round_id: number;
  handicap_bucket: number;
  strokes_gained: {
    total: number;
    by_category: Record<SGCategory, number>;
  };
  tiger_five: {
    double_bogeys_or_worse: number;
    three_putts: number;
    par_five_bogeys: number;
    blown_recoveries_inside_50: number;
    penalties_inside_150: number;
    clean_card_index: number;
  };
  putting: {
    lag_putt_count: number;
    lag_efficiency_pct: number | null;
    average_lag_proximity_yards: number | null;
    short_putt_count: number;
    start_line_conversion_pct: number | null;
  };
  shots: RoundShotAnalytics[];
}

export type RoundAnalyticsResponse = RoundAnalyticsPending | RoundAnalytics;

export function isPendingAnalytics(
  analytics: RoundAnalyticsResponse
): analytics is RoundAnalyticsPending {
  return "needs_shots" in analytics;
}

export interface DispersionEllipse {
  center_longitudinal_yards: number;
  center_lateral_yards: number;
  semi_major_yards: number;
  semi_minor_yards: number;
  k: number;
}

export interface ClubGappingStats {
  club: string;
  sample_count: number;
  excluded_outliers: number;
  carry_mean_yards: number;
  carry_median_yards: number;
  carry_stdev_yards: number;
  lateral_mean_yards: number | null;
  lateral_stdev_yards: number | null;
  dispersion_ellipse: DispersionEllipse | null;
}

export interface ClubGap {
  longer_club: string;
  shorter_club: string;
  carry_gap_yards: number;
}

export interface SmartBag {
  user_id: number;
  clubs: ClubGappingStats[];
  gaps: ClubGap[];
}

export interface FitUploadResult {
  round_id: number;
  status: RoundStatus;
  sport: string | null;
  point_count: number;
}

export interface HoleSummary {
  hole_number: number;
  par: number;
  yardage: number;
  shot_count: number;
}

export interface LatLngPoint {
  lat: number;
  lng: number;
}

export interface HoleReplayShot {
  shot_id: number;
  shot_number: number;
  club: string | null;
  start_lie: string;
  end_lie: string;
  start_distance_yards: number;
  end_distance_yards: number;
  strokes_gained: number | null;
  tag: string | null;
  approach_leave: ApproachLeave;
  location: LatLngPoint | null;
}

export interface HoleReplay {
  round_id: number;
  hole_number: number;
  par: number;
  yardage: number;
  tee: LatLngPoint | null;
  green_center: LatLngPoint | null;
  green_boundary: LatLngPoint[] | null;
  shots: HoleReplayShot[];
  short_sided_count: number;
}

// --- Course builder + manual round entry (PRD §10 Phase 5) ---
//
// Garmin's OAuth API (Phase 3) turned out to require a paid developer
// account, so manual entry is now the primary way round data gets in:
// pick or create a course (optionally prefilled from OpenStreetMap), create
// a round against it, then submit shots hole-by-hole.

export interface CourseListItem {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
}

export interface HoleGeometry {
  tee: LatLngPoint | null;
  green_center: LatLngPoint | null;
  green_boundary: LatLngPoint[] | null;
}

export interface CourseHoleDetail extends HoleGeometry {
  hole_number: number;
  par: number;
  yardage: number;
}

export interface CourseDetail {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
  osm_relation_id: number | null;
  holes: CourseHoleDetail[];
}

export interface HoleCreateInput {
  number: number;
  par: number;
  yardage: number;
  tee_location?: LatLngPoint | null;
  green_center?: LatLngPoint | null;
  green_boundary?: LatLngPoint[] | null;
}

export interface CourseCreateInput {
  name: string;
  city?: string | null;
  state?: string | null;
  osm_relation_id?: number | null;
  holes: HoleCreateInput[];
}

export interface OsmCourseSummary {
  osm_type: "way" | "relation" | "node";
  osm_id: number;
  name: string;
  city: string | null;
  state: string | null;
  // Lets a map center itself on the course before any hole geometry has
  // been fetched or built.
  center: LatLngPoint | null;
}

// A draft, not yet persisted — OSM coverage is inconsistent, so every field
// but the hole's identity may be missing and needs review before it's
// submitted to `createCourse`.
export interface OsmHoleCandidate {
  number: number | null;
  par: number | null;
  yardage: number | null;
  tee_location: LatLngPoint | null;
  green_center: LatLngPoint | null;
  green_boundary: LatLngPoint[] | null;
}

export interface OsmCourseDraft {
  name: string;
  city: string | null;
  state: string | null;
  osm_relation_id: number;
  holes: OsmHoleCandidate[];
}

export interface RoundCreateInput {
  user_id: number;
  course_id: number;
  played_at?: string;
  total_score?: number | null;
  status?: RoundStatus;
}

export interface ShotCreateInput {
  hole_number: number;
  shot_number: number;
  club?: string | null;
  start_lie: Lie;
  end_lie: Lie;
  start_distance_yards: number;
  end_distance_yards: number;
  location?: LatLngPoint | null;
  tag?: string | null;
}

export interface CreatedShot {
  id: number;
  hole_id: number;
  shot_number: number;
  club: string | null;
  start_lie: Lie;
  end_lie: Lie;
  start_distance_yards: number;
  end_distance_yards: number;
  strokes_gained: number | null;
  tag: string | null;
  location: LatLngPoint | null;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// FastAPI error bodies are JSON: `{"detail": "message"}` for a plain
// HTTPException, or `{"detail": [{"msg": "...", ...}, ...]}` for a Pydantic
// validation error (422). Extract a readable message from either shape,
// falling back to the raw response body if it isn't JSON at all.
function extractErrorMessage(responseText: string): string {
  try {
    const body = JSON.parse(responseText) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : ""))
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    // not JSON — fall through to the raw text
  }
  return responseText;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, extractErrorMessage(text) || response.statusText);
  }
  return (await response.json()) as T;
}

export function getRounds(): Promise<RoundSummary[]> {
  return apiFetch<RoundSummary[]>("/api/rounds");
}

export function getRoundAnalytics(roundId: number): Promise<RoundAnalyticsResponse> {
  return apiFetch<RoundAnalyticsResponse>(`/api/rounds/${roundId}/analytics`);
}

export function getSmartBag(userId: number): Promise<SmartBag> {
  return apiFetch<SmartBag>(`/api/bag/${userId}`);
}

export function getRoundHoles(roundId: number): Promise<HoleSummary[]> {
  return apiFetch<HoleSummary[]>(`/api/rounds/${roundId}/holes`);
}

export function getHoleReplay(roundId: number, holeNumber: number): Promise<HoleReplay> {
  return apiFetch<HoleReplay>(`/api/rounds/${roundId}/holes/${holeNumber}/replay`);
}

export function uploadFitFile(userId: number, file: File): Promise<FitUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<FitUploadResult>(`/api/rounds/upload?user_id=${userId}`, {
    method: "POST",
    body: formData,
  });
}

export function getCourses(): Promise<CourseListItem[]> {
  return apiFetch<CourseListItem[]>("/api/courses");
}

export function getCourse(courseId: number): Promise<CourseDetail> {
  return apiFetch<CourseDetail>(`/api/courses/${courseId}`);
}

export function createCourse(payload: CourseCreateInput): Promise<CourseDetail> {
  return apiFetch<CourseDetail>("/api/courses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function searchOsmCourses(query: string): Promise<OsmCourseSummary[]> {
  return apiFetch<OsmCourseSummary[]>(
    `/api/courses/search-osm?q=${encodeURIComponent(query)}`
  );
}

export function getOsmCourseGeometry(
  osmType: OsmCourseSummary["osm_type"],
  osmId: number
): Promise<OsmCourseDraft> {
  return apiFetch<OsmCourseDraft>(`/api/courses/search-osm/${osmType}/${osmId}`);
}

export function createRound(payload: RoundCreateInput): Promise<RoundSummary> {
  return apiFetch<RoundSummary>("/api/rounds", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function submitRoundShots(
  roundId: number,
  shots: ShotCreateInput[]
): Promise<CreatedShot[]> {
  return apiFetch<CreatedShot[]>(`/api/rounds/${roundId}/shots/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shots }),
  });
}

export interface GarminAuthorizeResult {
  authorize_url: string;
}

export interface GarminStatus {
  connected: boolean;
}

export function startGarminAuthorize(userId: number): Promise<GarminAuthorizeResult> {
  return apiFetch<GarminAuthorizeResult>(`/api/auth/garmin/authorize?user_id=${userId}`);
}

export function getGarminStatus(userId: number): Promise<GarminStatus> {
  return apiFetch<GarminStatus>(`/api/auth/garmin/${userId}/status`);
}

export function disconnectGarmin(userId: number): Promise<GarminStatus> {
  return apiFetch<GarminStatus>(`/api/auth/garmin/${userId}`, { method: "DELETE" });
}

// --- Practice Hub: R10/R50 delivery profile + combines (PRD §6.1, §7.1, §10 Phase 6) ---

export interface ClubDeliveryProfile {
  club: string;
  shot_count: number;
  avg_club_path_deg: number | null;
  avg_face_angle_deg: number | null;
  avg_face_to_path_deg: number | null;
  avg_spin_axis_deg: number | null;
  avg_smash_factor: number | null;
  avg_carry_yards: number | null;
}

export interface DeliveryTrendPoint {
  session_id: number;
  recorded_at: string;
  shot_count: number;
  avg_carry_yards: number | null;
  avg_smash_factor: number | null;
  avg_face_to_path_deg: number | null;
  avg_spin_axis_deg: number | null;
}

export interface SimVsRealGapping {
  club: string;
  range_carry_mean_yards: number | null;
  on_course_carry_mean_yards: number | null;
  delta_yards: number | null;
}

export interface DeliveryProfile {
  user_id: number;
  session_count: number;
  clubs: ClubDeliveryProfile[];
  trend: Record<string, DeliveryTrendPoint[]>;
  sim_vs_real_gapping: SimVsRealGapping[];
}

export function getDeliveryProfile(userId: number): Promise<DeliveryProfile> {
  return apiFetch<DeliveryProfile>(`/api/practice/delivery/${userId}`);
}

export interface PracticeUploadResult {
  session_id: number;
  shot_count: number;
  errors: string[];
}

export function uploadPracticeSession(
  userId: number,
  source: string,
  file: File
): Promise<PracticeUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<PracticeUploadResult>(
    `/api/practice/sessions/upload?user_id=${userId}&source=${encodeURIComponent(source)}`,
    { method: "POST", body: formData }
  );
}

export type Weakness =
  | "approach_100_125"
  | "driver_dispersion"
  | "iron_strike_quality"
  | "putting_lag_speed";

export interface WeaknessSignal {
  weakness: Weakness;
  detail: string;
}

export interface Combine {
  weakness: Weakness;
  name: string;
  instructions: string;
  target_metric: string;
  video_search_url: string;
}

export interface PracticeCombines {
  user_id: number;
  weaknesses: WeaknessSignal[];
  combines: Combine[];
}

export function getPracticeCombines(userId: number): Promise<PracticeCombines> {
  return apiFetch<PracticeCombines>(`/api/practice/combines/${userId}`);
}

// --- Virtual/Sim Round Hub (PRD §6.2, §10 Phase 6) ---
//
// Deliberately a separate table and separate endpoints from Round/RoundStatus
// above — see app/models/virtual_round.py for why this is never allowed to
// feed a real-world handicap calculation.

export type SimPlatform = "home_tee_hero" | "e6" | "gspro" | "other";

export interface VirtualRound {
  id: number;
  user_id: number;
  platform: SimPlatform;
  course_name: string;
  played_at: string;
  holes_played: number;
  total_score: number | null;
  notes: string | null;
}

export interface VirtualRoundCreateInput {
  user_id: number;
  platform: SimPlatform;
  course_name: string;
  played_at?: string;
  holes_played?: number;
  total_score?: number | null;
  notes?: string | null;
}

export function getVirtualRounds(userId: number): Promise<VirtualRound[]> {
  return apiFetch<VirtualRound[]>(`/api/virtual-rounds?user_id=${userId}`);
}

export function createVirtualRound(payload: VirtualRoundCreateInput): Promise<VirtualRound> {
  return apiFetch<VirtualRound>("/api/virtual-rounds", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export { API_URL };
