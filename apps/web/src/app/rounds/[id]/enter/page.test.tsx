import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IDBFactory } from "fake-indexeddb";
import { useParams, useRouter } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getHoleReplay,
  getRoundHoles,
  submitRoundShots,
  type CreatedShot,
  type HoleReplay,
  type HoleSummary,
} from "@/lib/api";
import EnterRoundPage from "./page";

vi.mock("mapbox-gl/dist/mapbox-gl.css", () => ({}));
vi.mock("mapbox-gl", () => ({
  default: { accessToken: "", Map: vi.fn(), Marker: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
  useRouter: vi.fn(),
  usePathname: () => "/rounds/42/enter",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getRoundHoles: vi.fn(),
    getHoleReplay: vi.fn(),
    submitRoundShots: vi.fn(),
  };
});

const mockUseParams = vi.mocked(useParams);
const mockUseRouter = vi.mocked(useRouter);
const mockGetRoundHoles = vi.mocked(getRoundHoles);
const mockGetHoleReplay = vi.mocked(getHoleReplay);
const mockSubmitRoundShots = vi.mocked(submitRoundShots);

const holes: HoleSummary[] = [
  { hole_number: 1, par: 4, yardage: 400, shot_count: 0 },
  { hole_number: 2, par: 3, yardage: 175, shot_count: 0 },
];

function makeReplay(overrides: Partial<HoleReplay> = {}): HoleReplay {
  return {
    round_id: 42, hole_number: 1, par: 4, yardage: 400,
    tee: { lat: 33.7, lng: -78.9 }, green_center: { lat: 33.7025, lng: -78.9 },
    green_boundary: null, shots: [], short_sided_count: 0,
    ...overrides,
  };
}

const mockPush = vi.fn();

beforeEach(() => {
  globalThis.indexedDB = new IDBFactory();
  mockPush.mockReset();
  mockUseParams.mockReturnValue({ id: "42" });
  mockUseRouter.mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
  mockGetRoundHoles.mockReset();
  mockGetHoleReplay.mockReset();
  mockSubmitRoundShots.mockReset();
  Element.prototype.getBoundingClientRect = vi.fn(() => ({
    left: 0, top: 0, width: 320, height: 480, right: 320, bottom: 480, x: 0, y: 0,
    toJSON: () => {},
  }));
});

describe("EnterRoundPage", () => {
  it("renders the round id and loads holes", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockResolvedValue(makeReplay());

    render(<EnterRoundPage />);

    expect(screen.getByText("Enter round #42")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "2" })).toBeInTheDocument();
  });

  it("shows the shot-entry map for the first hole automatically", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockResolvedValue(makeReplay());

    render(<EnterRoundPage />);

    expect(await screen.findByRole("img", { name: "Hole 1 replay" })).toBeInTheDocument();
    expect(mockGetHoleReplay).toHaveBeenCalledWith(42, 1);
  });

  it("adds a shot with a GPS location and lists it", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockResolvedValue(makeReplay());
    const user = userEvent.setup();

    render(<EnterRoundPage />);
    await screen.findByRole("img", { name: "Hole 1 replay" });

    fireEvent.click(screen.getByRole("img", { name: "Hole 1 replay" }), {
      clientX: 160, clientY: 240,
    });
    await user.type(screen.getByLabelText("Club"), "Driver");
    await user.type(screen.getByLabelText("Start distance (yd)"), "400");
    await user.type(screen.getByLabelText("End distance (yd)"), "150");
    await user.click(screen.getByRole("button", { name: "Add shot" }));

    expect(await screen.findByText(/Driver/, { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText(/pinned/, { selector: "span" })).toBeInTheDocument();
  });

  it("switches holes and fetches that hole's geometry", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockImplementation((_roundId, holeNumber) =>
      Promise.resolve(makeReplay({ hole_number: holeNumber }))
    );
    const user = userEvent.setup();

    render(<EnterRoundPage />);
    await screen.findByRole("img", { name: "Hole 1 replay" });

    await user.click(screen.getByRole("button", { name: "2" }));

    expect(await screen.findByRole("img", { name: "Hole 2 replay" })).toBeInTheDocument();
    expect(mockGetHoleReplay).toHaveBeenCalledWith(42, 2);
  });

  it("submits the round and redirects to the round detail page", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockResolvedValue(makeReplay());
    mockSubmitRoundShots.mockResolvedValue([] as CreatedShot[]);
    const user = userEvent.setup();

    render(<EnterRoundPage />);
    await screen.findByRole("img", { name: "Hole 1 replay" });

    await user.type(screen.getByLabelText("Start distance (yd)"), "400");
    await user.type(screen.getByLabelText("End distance (yd)"), "150");
    await user.click(screen.getByRole("button", { name: "Add shot" }));

    const submitButton = await screen.findByRole("button", { name: /submit round/i });
    await user.click(submitButton);

    expect(mockSubmitRoundShots).toHaveBeenCalledWith(
      42,
      expect.arrayContaining([
        expect.objectContaining({ hole_number: 1, start_distance_yards: 400 }),
      ])
    );
    expect(mockPush).toHaveBeenCalledWith("/rounds/42");
  });

  it("removes a shot from the list", async () => {
    mockGetRoundHoles.mockResolvedValue(holes);
    mockGetHoleReplay.mockResolvedValue(makeReplay());
    const user = userEvent.setup();

    render(<EnterRoundPage />);
    await screen.findByRole("img", { name: "Hole 1 replay" });

    await user.type(screen.getByLabelText("Start distance (yd)"), "400");
    await user.type(screen.getByLabelText("End distance (yd)"), "150");
    await user.click(screen.getByRole("button", { name: "Add shot" }));

    expect(await screen.findByRole("button", { name: "Remove" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove" }));

    expect(screen.queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
  });
});
