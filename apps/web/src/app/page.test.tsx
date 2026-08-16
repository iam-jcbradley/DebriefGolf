import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardPage from "./page";
import { getRoundAnalytics, getRounds } from "@/lib/api";
import type { RoundAnalytics, RoundSummary } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getRounds: vi.fn(),
    getRoundAnalytics: vi.fn(),
  };
});

vi.mock("@/lib/current-user", () => ({
  useCurrentUser: vi.fn(),
}));

const mockGetRounds = vi.mocked(getRounds);
const mockGetRoundAnalytics = vi.mocked(getRoundAnalytics);
const mockUseCurrentUser = vi.mocked(useCurrentUser);

const testUser = { id: 7, name: "Jane Doe", email: "player@example.com", handicap_index: 0, created_at: "2026-01-01T00:00:00Z" };

const olderRound: RoundSummary = {
  id: 1, played_at: "2026-08-01T00:00:00Z", total_score: 90,
  course_id: 1, user_id: 7, status: "verified",
};
const recentRound: RoundSummary = {
  id: 2, played_at: "2026-08-15T00:00:00Z", total_score: 78,
  course_id: 1, user_id: 7, status: "verified",
};

const readyAnalytics: RoundAnalytics = {
  round_id: 2,
  handicap_bucket: 5,
  strokes_gained: { total: 1.5, by_category: { OTT: 1, APP: 0.5, ARG: 0, PUTT: 0 } },
  tiger_five: {
    double_bogeys_or_worse: 0, three_putts: 0, par_five_bogeys: 0,
    blown_recoveries_inside_50: 0, penalties_inside_150: 0, clean_card_index: 100,
  },
  putting: {
    lag_putt_count: 0, lag_efficiency_pct: null, average_lag_proximity_yards: null,
    short_putt_count: 0, start_line_conversion_pct: null,
  },
  shots: [],
};

beforeEach(() => {
  mockGetRounds.mockReset();
  mockGetRoundAnalytics.mockReset();
  mockUseCurrentUser.mockReturnValue({
    user: testUser,
    loading: false,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  });
});

describe("DashboardPage", () => {
  it("shows the signed-out empty state when nobody is signed in", () => {
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      refresh: vi.fn(),
    });
    render(<DashboardPage />);
    expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
    expect(mockGetRounds).not.toHaveBeenCalled();
  });

  it("shows a loading state before data arrives", () => {
    mockGetRounds.mockReturnValue(new Promise(() => {})); // never resolves
    render(<DashboardPage />);
    expect(screen.getByText(/Loading your round/)).toBeInTheDocument();
  });

  it("shows an empty state when there are no rounds", async () => {
    mockGetRounds.mockResolvedValue([]);
    render(<DashboardPage />);
    expect(await screen.findByText("No rounds logged yet.")).toBeInTheDocument();
  });

  it("fetches the signed-in player's rounds", async () => {
    mockGetRounds.mockResolvedValue([recentRound]);
    mockGetRoundAnalytics.mockResolvedValue(readyAnalytics);

    render(<DashboardPage />);

    await screen.findByText("Round Snapshot");
    // Only the latest round is fetched — not every round ever played.
    expect(mockGetRounds).toHaveBeenCalledWith({ limit: 1 });
  });

  it("fetches analytics for the round the API returns first", async () => {
    // Ordering is the server's job now (`ORDER BY played_at DESC LIMIT 1`),
    // not a client-side sort over the full list — see the backend's
    // test_list_rounds_returns_only_the_callers_rounds for that guarantee.
    mockGetRounds.mockResolvedValue([recentRound, olderRound]);
    mockGetRoundAnalytics.mockResolvedValue(readyAnalytics);

    render(<DashboardPage />);

    await screen.findByText("Round Snapshot");
    expect(mockGetRoundAnalytics).toHaveBeenCalledWith(recentRound.id);
    expect(mockGetRoundAnalytics).not.toHaveBeenCalledWith(olderRound.id);
  });

  it("shows an audit-needed message when the round has no shots yet", async () => {
    mockGetRounds.mockResolvedValue([recentRound]);
    mockGetRoundAnalytics.mockResolvedValue({
      round_id: 2, status: "needs_audit", needs_shots: true,
    });

    render(<DashboardPage />);

    expect(await screen.findByText("Round uploaded — audit needed")).toBeInTheDocument();
  });

  it("renders the Round Snapshot and Tiger 5 meter once analytics are ready", async () => {
    mockGetRounds.mockResolvedValue([recentRound]);
    mockGetRoundAnalytics.mockResolvedValue(readyAnalytics);

    render(<DashboardPage />);

    expect(await screen.findByText("Round Snapshot")).toBeInTheDocument();
    expect(screen.getByText("Tiger 5 Disaster Meter")).toBeInTheDocument();
  });

  it("shows an error message when fetching fails", async () => {
    mockGetRounds.mockRejectedValue(new Error("network down"));

    render(<DashboardPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("network down");
  });
});
