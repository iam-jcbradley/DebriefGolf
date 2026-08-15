import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { HoleReplay } from "@/lib/api";
import { HoleReplaySvg } from "./hole-replay-svg";

const baseHole: HoleReplay = {
  round_id: 1,
  hole_number: 7,
  par: 4,
  yardage: 400,
  tee: { lat: 33.7, lng: -78.9 },
  green_center: { lat: 33.7025, lng: -78.9 }, // ~277y due north
  green_boundary: [
    { lat: 33.70255, lng: -78.90005 },
    { lat: 33.70255, lng: -78.89995 },
    { lat: 33.70245, lng: -78.89995 },
    { lat: 33.70245, lng: -78.90005 },
  ],
  shots: [
    {
      shot_id: 1, shot_number: 1, club: "Driver", start_lie: "tee", end_lie: "fairway",
      start_distance_yards: 400, end_distance_yards: 150, strokes_gained: 0.4, tag: null,
      approach_leave: "unclassified", location: { lat: 33.7013, lng: -78.9001 },
    },
    {
      shot_id: 2, shot_number: 2, club: "7-Iron", start_lie: "fairway", end_lie: "sand",
      start_distance_yards: 150, end_distance_yards: 8, strokes_gained: -0.8, tag: "Heel",
      approach_leave: "short_sided", location: { lat: 33.7022, lng: -78.9002 },
    },
    {
      shot_id: 3, shot_number: 3, club: null, start_lie: "penalty", end_lie: "penalty",
      start_distance_yards: 140, end_distance_yards: 140, strokes_gained: -1.0, tag: "Penalty",
      approach_leave: "unclassified", location: null, // no recorded position
    },
  ],
  short_sided_count: 1,
};

describe("HoleReplaySvg", () => {
  it("renders a message instead of a map when tee/green geometry is missing", () => {
    render(<HoleReplaySvg hole={{ ...baseHole, tee: null }} />);
    expect(
      screen.getByText(/doesn't have tee\/green geometry recorded yet/)
    ).toBeInTheDocument();
  });

  it("renders an accessible svg labeled with the hole number", () => {
    render(<HoleReplaySvg hole={baseHole} />);
    expect(screen.getByRole("img", { name: "Hole 7 replay" })).toBeInTheDocument();
  });

  it("renders one circle marker per shot that has a location, skipping shots without one", () => {
    const { container } = render(<HoleReplaySvg hole={baseHole} />);
    // 2 shot markers (tee + green markers are separate circles, +2 = 4 total)
    const titles = container.querySelectorAll("circle title");
    expect(titles).toHaveLength(2);
  });

  it("renders the green boundary as a polygon when provided", () => {
    const { container } = render(<HoleReplaySvg hole={baseHole} />);
    expect(container.querySelector("polygon")).not.toBeNull();
  });

  it("omits the green boundary polygon when not provided", () => {
    const { container } = render(<HoleReplaySvg hole={{ ...baseHole, green_boundary: null }} />);
    expect(container.querySelector("polygon")).toBeNull();
  });

  it("renders a dispersion ellipse when one is passed", () => {
    const { container } = render(
      <HoleReplaySvg
        hole={baseHole}
        ellipse={{
          center_longitudinal_yards: 150, center_lateral_yards: 3,
          semi_major_yards: 15, semi_minor_yards: 8, k: 1.5,
        }}
      />
    );
    expect(container.querySelector('[data-testid="dispersion-ellipse"]')).not.toBeNull();
  });

  it("omits the dispersion ellipse when none is passed", () => {
    const { container } = render(<HoleReplaySvg hole={baseHole} />);
    expect(container.querySelector('[data-testid="dispersion-ellipse"]')).toBeNull();
  });

  it("anchors the ellipse away from the tee when ellipseAnchorYards is given", () => {
    // A carry-relative ellipse (mean 0,0) anchored at 200y from the tee
    // should render far from an unanchored one (which defaults to the tee).
    const props = {
      hole: baseHole,
      ellipse: {
        center_longitudinal_yards: 0, center_lateral_yards: 0,
        semi_major_yards: 5, semi_minor_yards: 5, k: 1.5,
      },
    };
    const { container: unanchored } = render(<HoleReplaySvg {...props} />);
    const { container: anchored } = render(
      <HoleReplaySvg {...props} ellipseAnchorYards={{ longitudinal: 200, lateral: 0 }} />
    );

    const unanchoredCy = unanchored.querySelector("ellipse")?.getAttribute("cy");
    const anchoredCy = anchored.querySelector("ellipse")?.getAttribute("cy");
    expect(anchoredCy).not.toBeNull();
    expect(anchoredCy).not.toEqual(unanchoredCy);
  });

  describe("onPick", () => {
    beforeEach(() => {
      Element.prototype.getBoundingClientRect = vi.fn(() => ({
        left: 0, top: 0, width: 320, height: 480, right: 320, bottom: 480, x: 0, y: 0,
        toJSON: () => {},
      }));
    });

    it("does not attach a click handler when onPick is omitted", () => {
      render(<HoleReplaySvg hole={baseHole} />);
      // clicking shouldn't throw even without a handler
      fireEvent.click(screen.getByRole("img"), { clientX: 160, clientY: 240 });
    });

    it("reports a clicked point's lat/lng near the green for a click at the top", () => {
      const onPick = vi.fn();
      render(<HoleReplaySvg hole={baseHole} onPick={onPick} />);

      fireEvent.click(screen.getByRole("img"), { clientX: 160, clientY: 40 });

      expect(onPick).toHaveBeenCalledTimes(1);
      const [{ lat }] = onPick.mock.calls[0];
      // green is due north of the tee (higher latitude); a click near the
      // top of the SVG should resolve closer to the green than the tee.
      expect(lat).toBeGreaterThan(baseHole.tee!.lat);
    });
  });
});
