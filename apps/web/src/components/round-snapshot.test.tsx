import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RoundAnalytics, RoundSummary } from "@/lib/api";
import { RoundSnapshot } from "./round-snapshot";

const round: RoundSummary = {
  id: 6,
  played_at: "2026-08-15T00:00:00Z",
  total_score: 78,
  course_id: 1,
  user_id: 1,
  status: "verified",
};

const analytics: RoundAnalytics = {
  round_id: 6,
  handicap_bucket: 5,
  strokes_gained: {
    total: -2.69,
    by_category: { OTT: 6.21, APP: -2.52, ARG: 0.91, PUTT: -7.29 },
  },
  tiger_five: {
    double_bogeys_or_worse: 1,
    three_putts: 1,
    par_five_bogeys: 1,
    blown_recoveries_inside_50: 0,
    penalties_inside_150: 1,
    clean_card_index: 66.7,
  },
  putting: {
    lag_putt_count: 14,
    lag_efficiency_pct: 7.1,
    average_lag_proximity_yards: 1.26,
    short_putt_count: 17,
    start_line_conversion_pct: 100,
  },
  shots: [],
};

describe("RoundSnapshot", () => {
  it("leads with the score as the headline numeral, not buried in body text", () => {
    render(<RoundSnapshot round={round} analytics={analytics} />);
    expect(screen.getByText("78")).toBeInTheDocument();
    expect(screen.getByText(/vs 5 handicap/)).toBeInTheDocument();
  });

  it("names the round by course and date so it identifies itself", () => {
    render(
      <RoundSnapshot round={round} analytics={analytics} courseName="Pinehurst Creek Golf Club" />
    );
    expect(screen.getByText("Pinehurst Creek Golf Club")).toBeInTheDocument();
    // Rendered via toLocaleDateString, so assert on the year rather than a
    // full formatted string that shifts with the runner's locale.
    expect(screen.getByText(/2026/)).toBeInTheDocument();
  });

  it("shows score to par when the course par is known", () => {
    render(<RoundSnapshot round={round} analytics={analytics} coursePar={72} />);
    expect(screen.getByText("+6")).toBeInTheDocument();
  });

  it("omits the to-par figure when no course par is available", () => {
    render(<RoundSnapshot round={round} analytics={analytics} coursePar={null} />);
    expect(screen.queryByText("+6")).not.toBeInTheDocument();
  });

  it("renders all four SG categories with signed values", () => {
    render(<RoundSnapshot round={round} analytics={analytics} />);
    expect(screen.getByText("Off the Tee")).toBeInTheDocument();
    expect(screen.getByText("+6.21")).toBeInTheDocument();
    expect(screen.getByText("Approach")).toBeInTheDocument();
    expect(screen.getByText("-2.52")).toBeInTheDocument();
    expect(screen.getByText("Around the Green")).toBeInTheDocument();
    expect(screen.getByText("+0.91")).toBeInTheDocument();
    expect(screen.getByText("Putting")).toBeInTheDocument();
    expect(screen.getByText("-7.29")).toBeInTheDocument();
  });

  it("renders the total strokes gained", () => {
    render(<RoundSnapshot round={round} analytics={analytics} />);
    expect(screen.getByText("-2.69")).toBeInTheDocument();
  });

  it("renders a dash when there is no total score", () => {
    render(
      <RoundSnapshot round={{ ...round, total_score: null }} analytics={analytics} />
    );
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
