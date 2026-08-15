import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RoundAnalytics, RoundSummary } from "@/lib/api";
import { getPracticeCombines } from "@/lib/api";
import { CoachBriefButton } from "./coach-brief-button";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getPracticeCombines: vi.fn() };
});

const mockToBlob = vi.fn();
vi.mock("@react-pdf/renderer", () => ({
  pdf: () => ({ toBlob: mockToBlob }),
}));
vi.mock("@/lib/coach-brief/coach-brief-document", () => ({
  CoachBriefDocument: () => null,
}));

const mockGetPracticeCombines = vi.mocked(getPracticeCombines);

const round: RoundSummary = {
  id: 6,
  played_at: "2026-08-15T00:00:00Z",
  total_score: 78,
  course_id: 1,
  user_id: 42,
  status: "verified",
};

const analytics: RoundAnalytics = {
  round_id: 6,
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
  shots: [],
};

beforeEach(() => {
  mockToBlob.mockReset();
  mockGetPracticeCombines.mockReset();
  vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:mock"), revokeObjectURL: vi.fn() });
});

describe("CoachBriefButton", () => {
  it("generates a PDF and triggers a download on click", async () => {
    mockToBlob.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
    mockGetPracticeCombines.mockResolvedValue({ user_id: 42, weaknesses: [], combines: [] });
    const user = userEvent.setup();

    render(<CoachBriefButton round={round} analytics={analytics} />);
    await user.click(screen.getByRole("button", { name: /download coach-ready brief/i }));

    expect(await screen.findByRole("button", { name: /download coach-ready brief/i })).toBeEnabled();
    expect(mockGetPracticeCombines).toHaveBeenCalledWith(42);
    expect(mockToBlob).toHaveBeenCalled();
  });

  it("still generates a brief when the combines fetch fails", async () => {
    mockToBlob.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
    mockGetPracticeCombines.mockRejectedValue(new Error("network error"));
    const user = userEvent.setup();

    render(<CoachBriefButton round={round} analytics={analytics} />);
    await user.click(screen.getByRole("button", { name: /download coach-ready brief/i }));

    expect(await screen.findByRole("button", { name: /download coach-ready brief/i })).toBeEnabled();
    expect(mockToBlob).toHaveBeenCalled();
  });

  it("shows an error when PDF generation fails", async () => {
    mockToBlob.mockRejectedValue(new Error("render failed"));
    mockGetPracticeCombines.mockResolvedValue({ user_id: 42, weaknesses: [], combines: [] });
    const user = userEvent.setup();

    render(<CoachBriefButton round={round} analytics={analytics} />);
    await user.click(screen.getByRole("button", { name: /download coach-ready brief/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/failed to generate/i);
  });
});
