import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useParams } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getHoleReplay,
  getRoundHoles,
  getRounds,
  getSmartBag,
  type HoleReplay,
  type HoleSummary,
  type RoundSummary,
  type SmartBag,
} from "@/lib/api";
import RoundDetailPage from "./page";

vi.mock("mapbox-gl/dist/mapbox-gl.css", () => ({}));
vi.mock("mapbox-gl", () => ({
  default: {
    accessToken: "",
    Map: vi.fn(),
    Marker: vi.fn(),
  },
}));

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
  usePathname: () => "/rounds/1",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getRoundHoles: vi.fn(),
    getHoleReplay: vi.fn(),
    getRounds: vi.fn(),
    getSmartBag: vi.fn(),
  };
});

const mockUseParams = vi.mocked(useParams);
const mockGetRoundHoles = vi.mocked(getRoundHoles);
const mockGetHoleReplay = vi.mocked(getHoleReplay);
const mockGetRounds = vi.mocked(getRounds);
const mockGetSmartBag = vi.mocked(getSmartBag);

const holes: HoleSummary[] = [
  { hole_number: 1, par: 4, yardage: 400, shot_count: 4 },
  { hole_number: 2, par: 3, yardage: 175, shot_count: 3 },
];

function makeReplay(overrides: Partial<HoleReplay> = {}): HoleReplay {
  return {
    round_id: 1, hole_number: 1, par: 4, yardage: 400,
    tee: { lat: 33.7, lng: -78.9 }, green_center: { lat: 33.7025, lng: -78.9 },
    green_boundary: null, shots: [], short_sided_count: 0,
    ...overrides,
  };
}

beforeEach(() => {
  mockUseParams.mockReturnValue({ id: "1" });
  mockGetRoundHoles.mockReset();
  mockGetHoleReplay.mockReset();
  mockGetRounds.mockReset();
  mockGetSmartBag.mockReset();
  mockGetRounds.mockResolvedValue([]);
  mockGetSmartBag.mockResolvedValue({ user_id: 1, clubs: [], gaps: [] } as SmartBag);
});

describe("RoundDetailPage", () => {
  it("renders the round id in the heading", () => {
    mockGetRoundHoles.mockReturnValue(new Promise(() => {}));
    render(<RoundDetailPage />);
    expect(screen.getByText("Round #1 — Hole Replay")).toBeInTheDocument();
  });

  it("shows a message when the round has no course assigned", async () => {
    mockGetRoundHoles.mockResolvedValue([]);
    render(<RoundDetailPage />);
    expect(await screen.findByText(/no course assigned yet/)).toBeInTheDocument();
  });

  it("selects the first hole automatically and renders its replay", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockResolvedValue(makeReplay());

    render(<RoundDetailPage />);

    expect(await screen.findByRole("img", { name: "Hole 1 replay" })).toBeInTheDocument();
    expect(mockGetHoleReplay).toHaveBeenCalledWith(1, 1);
  });

  it("switches holes when a hole button is clicked", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockImplementation((_roundId, holeNumber) =>
      Promise.resolve(makeReplay({ hole_number: holeNumber }))
    );
    const user = userEvent.setup();

    render(<RoundDetailPage />);
    await screen.findByRole("img", { name: "Hole 1 replay" });

    await user.click(screen.getByRole("button", { name: "2" }));

    expect(await screen.findByRole("img", { name: "Hole 2 replay" })).toBeInTheDocument();
    expect(mockGetHoleReplay).toHaveBeenCalledWith(1, 2);
  });

  it("shows the short-sided banner when the hole reports a short-sided miss", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockResolvedValue(makeReplay({ short_sided_count: 1 }));

    render(<RoundDetailPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Short-sided miss on hole 1");
  });

  it("does not show the short-sided banner when there are no short-sided misses", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockResolvedValue(makeReplay({ short_sided_count: 0 }));

    render(<RoundDetailPage />);
    await screen.findByRole("img", { name: "Hole 1 replay" });

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("fetches a dispersion ellipse for the approach club when one reached the green", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockResolvedValue(
      makeReplay({
        shots: [
          {
            shot_id: 1, shot_number: 1, club: "7-Iron", start_lie: "fairway", end_lie: "green",
            start_distance_yards: 150, end_distance_yards: 6, strokes_gained: 0.3, tag: null,
            approach_leave: "on_green", location: null,
          },
        ],
      })
    );
    mockGetRounds.mockResolvedValue([
      { id: 1, played_at: "2026-08-15", total_score: 72, course_id: 1, user_id: 9, status: "verified" },
    ] as RoundSummary[]);
    mockGetSmartBag.mockResolvedValue({
      user_id: 9,
      clubs: [
        {
          club: "7-Iron", sample_count: 5, excluded_outliers: 0,
          carry_mean_yards: 150, carry_median_yards: 150, carry_stdev_yards: 5,
          lateral_mean_yards: 1, lateral_stdev_yards: 4,
          dispersion_ellipse: {
            center_longitudinal_yards: 150, center_lateral_yards: 1,
            semi_major_yards: 7.5, semi_minor_yards: 6, k: 1.5,
          },
        },
      ],
      gaps: [],
    });

    render(<RoundDetailPage />);

    await screen.findByRole("img", { name: "Hole 1 replay" });
    expect(mockGetSmartBag).toHaveBeenCalledWith(9);
  });
});
