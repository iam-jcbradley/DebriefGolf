import { describe, expect, it } from "vitest";
import type { HoleReplayShot } from "@/lib/api";
import { pickApproachClub, pickApproachShot } from "./approach-club";

function shot(overrides: Partial<HoleReplayShot>): HoleReplayShot {
  return {
    shot_id: 1, shot_number: 1, club: "7-Iron", start_lie: "fairway", end_lie: "green",
    start_distance_yards: 150, end_distance_yards: 6, strokes_gained: null, tag: null,
    approach_leave: "on_green", location: null,
    ...overrides,
  };
}

describe("pickApproachClub", () => {
  it("picks the club of the shot that reached the green", () => {
    const shots = [
      shot({ shot_number: 1, club: "Driver", end_lie: "fairway" }),
      shot({ shot_number: 2, club: "8-Iron", end_lie: "green" }),
      shot({ shot_number: 3, club: "Putter", start_lie: "green", end_lie: "hole" }),
    ];
    expect(pickApproachClub(shots)).toBe("8-Iron");
  });

  it("picks the club of the shot that reached the fringe", () => {
    const shots = [shot({ club: "6-Iron", end_lie: "fringe" })];
    expect(pickApproachClub(shots)).toBe("6-Iron");
  });

  it("returns null when no shot reached the green or fringe", () => {
    const shots = [shot({ club: "Driver", end_lie: "fairway" })];
    expect(pickApproachClub(shots)).toBeNull();
  });

  it("returns null for an empty shot list", () => {
    expect(pickApproachClub([])).toBeNull();
  });

  it("returns null when the approach shot has no club recorded", () => {
    const shots = [shot({ club: null, end_lie: "green" })];
    expect(pickApproachClub(shots)).toBeNull();
  });
});

describe("pickApproachShot", () => {
  it("returns the full shot object that reached the green", () => {
    const approach = shot({ shot_id: 42, club: "8-Iron", end_lie: "green" });
    expect(pickApproachShot([shot({ club: "Driver", end_lie: "fairway" }), approach])).toBe(
      approach
    );
  });

  it("returns null when no shot reached the green or fringe", () => {
    expect(pickApproachShot([shot({ end_lie: "fairway" })])).toBeNull();
  });
});
