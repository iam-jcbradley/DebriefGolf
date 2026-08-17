import { pdf } from "@react-pdf/renderer";
import { describe, expect, it } from "vitest";
import type { Combine, RoundAnalytics, RoundSummary } from "@/lib/api";
import { CoachBriefDocument } from "./coach-brief-document";

const round: RoundSummary = {
  id: 1,
  played_at: "2026-08-15T00:00:00Z",
  total_score: 78,
  course_id: 1,
  user_id: 1,
  status: "verified",
};

const analytics: RoundAnalytics = {
  round_id: 1,
  handicap_bucket: 5,
  strokes_gained: { total: -2.69, by_category: { OTT: 6.21, APP: -2.52, ARG: 0.91, PUTT: -7.29 } },
  tiger_five: {
    double_bogeys_or_worse: 1, three_putts: 1, par_five_bogeys: 1,
    blown_recoveries_inside_50: 0, penalties_inside_150: 1, clean_card_index: 66.7,
  },
  putting: {
    lag_putt_count: 14, lag_efficiency_pct: 7.1, average_lag_proximity_yards: 1.26,
    short_putt_count: 17, start_line_conversion_pct: 100,
  },
  shots: [
    { shot_id: 1, category: "APP", strokes_gained: -0.5, approach_leave: "unclassified",
      has_pin: false, has_green_boundary: false },
    { shot_id: 2, category: "APP", strokes_gained: -0.5, approach_leave: "short_sided",
      has_pin: false, has_green_boundary: false },
    { shot_id: 3, category: "APP", strokes_gained: 0.2, approach_leave: "on_green",
      has_pin: false, has_green_boundary: false },
  ],
};

const combine: Combine = {
  weakness: "putting_lag_speed",
  name: "Safety Circle Test",
  instructions: "Putt to a 3ft circle.",
  target_metric: "≥80% finish inside the 3ft ring",
  video_search_url: "https://example.com",
};

describe("CoachBriefDocument", () => {
  it("renders a well-formed single-page PDF", async () => {
    const blob = await pdf(
      <CoachBriefDocument round={round} analytics={analytics} combines={[combine]} />
    ).toBlob();

    expect(blob.type).toBe("application/pdf");
    const buffer = Buffer.from(await blob.arrayBuffer());
    expect(buffer.subarray(0, 5).toString()).toBe("%PDF-");
  });
});
