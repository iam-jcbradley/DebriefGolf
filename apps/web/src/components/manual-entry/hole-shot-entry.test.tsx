import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { HoleReplay } from "@/lib/api";
import type { DraftShot } from "@/lib/audit/types";
import { HoleShotEntry } from "./hole-shot-entry";

vi.mock("mapbox-gl/dist/mapbox-gl.css", () => ({}));
vi.mock("mapbox-gl", () => ({
  default: { accessToken: "", Map: vi.fn(), Marker: vi.fn() },
}));

const hole: HoleReplay = {
  round_id: 1,
  hole_number: 1,
  par: 4,
  yardage: 400,
  tee: { lat: 33.7, lng: -78.9 },
  green_center: { lat: 33.7025, lng: -78.9 },
  green_boundary: null,
  shots: [],
  short_sided_count: 0,
};

beforeEach(() => {
  Element.prototype.getBoundingClientRect = vi.fn(() => ({
    left: 0, top: 0, width: 320, height: 480, right: 320, bottom: 480, x: 0, y: 0,
    toJSON: () => {},
  }));
});

describe("HoleShotEntry", () => {
  it("renders the hole map (no token, so the SVG fallback)", () => {
    render(<HoleShotEntry hole={hole} draftShotsForHole={[]} onAdd={vi.fn()} />);
    expect(screen.getByRole("img", { name: "Hole 1 replay" })).toBeInTheDocument();
  });

  it("shows the not-yet-set message before any map click", () => {
    render(<HoleShotEntry hole={hole} draftShotsForHole={[]} onAdd={vi.fn()} />);
    expect(screen.getByText(/click the map to set/i)).toBeInTheDocument();
  });

  it("shows the picked location after a map click and includes it on submit", async () => {
    const onAdd = vi.fn();
    const user = userEvent.setup();
    render(<HoleShotEntry hole={hole} draftShotsForHole={[]} onAdd={onAdd} />);

    fireEvent.click(screen.getByRole("img", { name: "Hole 1 replay" }), {
      clientX: 160,
      clientY: 240,
    });
    expect(screen.getByText(/location set/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Club"), "7-Iron");
    await user.type(screen.getByLabelText("Start distance (yd)"), "150");
    await user.type(screen.getByLabelText("End distance (yd)"), "6");
    await user.click(screen.getByRole("button", { name: "Add shot" }));

    expect(onAdd).toHaveBeenCalledTimes(1);
    const submitted = onAdd.mock.calls[0][0];
    expect(submitted.club).toBe("7-Iron");
    expect(submitted.location).not.toBeNull();
  });

  it("submits a null location when the map was never clicked", async () => {
    const onAdd = vi.fn();
    const user = userEvent.setup();
    render(<HoleShotEntry hole={hole} draftShotsForHole={[]} onAdd={onAdd} />);

    await user.type(screen.getByLabelText("Start distance (yd)"), "150");
    await user.type(screen.getByLabelText("End distance (yd)"), "6");
    await user.click(screen.getByRole("button", { name: "Add shot" }));

    expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ location: null }));
  });

  it("clears the location when the clear link is clicked", async () => {
    const user = userEvent.setup();
    render(<HoleShotEntry hole={hole} draftShotsForHole={[]} onAdd={vi.fn()} />);

    fireEvent.click(screen.getByRole("img", { name: "Hole 1 replay" }), {
      clientX: 160,
      clientY: 240,
    });
    expect(screen.getByText(/location set/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "clear" }));
    expect(screen.getByText(/click the map to set/i)).toBeInTheDocument();
  });

  it("resets the form fields after adding a shot", async () => {
    const user = userEvent.setup();
    render(<HoleShotEntry hole={hole} draftShotsForHole={[]} onAdd={vi.fn()} />);

    await user.type(screen.getByLabelText("Club"), "7-Iron");
    await user.type(screen.getByLabelText("Start distance (yd)"), "150");
    await user.type(screen.getByLabelText("End distance (yd)"), "6");
    await user.click(screen.getByRole("button", { name: "Add shot" }));

    expect(screen.getByLabelText("Club")).toHaveValue("");
    expect(screen.getByLabelText("Start distance (yd)")).toHaveValue(null);
  });

  it("renders already-added draft shots for this hole as map preview markers", () => {
    const drafts: DraftShot[] = [
      {
        id: "a", holeNumber: 1, shotNumber: 1, club: "Driver",
        startLie: "tee", endLie: "fairway", startDistanceYards: 400, endDistanceYards: 150,
        location: { lat: 33.701, lng: -78.9001 },
      },
    ];
    const { container } = render(
      <HoleShotEntry hole={hole} draftShotsForHole={drafts} onAdd={vi.fn()} />
    );
    expect(container.querySelectorAll("circle title")).toHaveLength(1);
  });
});
