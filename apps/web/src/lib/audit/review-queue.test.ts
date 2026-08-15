import { describe, expect, it } from "vitest";
import {
  applyFringeIsolationResolution,
  applyPenaltyResolution,
  applyPuttRoutingResolution,
  applyStrikeQualityResolution,
  computeReviewQueue,
  markReviewed,
} from "./review-queue";
import type { DraftShot } from "./types";

function shot(overrides: Partial<DraftShot>): DraftShot {
  return {
    id: "s1",
    holeNumber: 1,
    shotNumber: 1,
    club: "7-Iron",
    startLie: "fairway",
    endLie: "green",
    startDistanceYards: 150,
    endDistanceYards: 6,
    ...overrides,
  };
}

describe("computeReviewQueue", () => {
  it("is empty for a fully-reviewed clean shot list", () => {
    const shots = [shot({ strokesGained: 0.3 })];
    expect(computeReviewQueue(shots)).toEqual([]);
  });

  it("surfaces a penalty item for an unreviewed hazard shot", () => {
    const shots = [shot({ id: "a", endLie: "penalty" })];
    expect(computeReviewQueue(shots)).toEqual([{ type: "penalty", shotId: "a" }]);
  });

  it("does not surface a penalty item once reviewed", () => {
    const shots = [shot({ id: "a", endLie: "penalty", penaltyReviewed: true })];
    expect(computeReviewQueue(shots)).toEqual([]);
  });

  it("surfaces a fringe isolation item for a putter used off the green", () => {
    const shots = [shot({ id: "a", club: "Putter", startLie: "fringe", endLie: "green" })];
    expect(computeReviewQueue(shots)).toEqual([{ type: "fringe_isolation", shotId: "a" }]);
  });

  it("surfaces a putt routing item for a confirmed green putt", () => {
    const shots = [
      shot({ id: "a", club: "Putter", startLie: "green", endLie: "hole", startDistanceYards: 1 }),
    ];
    expect(computeReviewQueue(shots)).toEqual([{ type: "putt_routing", shotId: "a" }]);
  });

  it("does not surface putt routing until fringe isolation is resolved", () => {
    const shots = [shot({ id: "a", club: "Putter", startLie: "fringe", endLie: "green" })];
    const queue = computeReviewQueue(shots);
    expect(queue).toHaveLength(1);
    expect(queue[0].type).toBe("fringe_isolation");
  });

  it("surfaces a strike quality item for a badly-struck shot", () => {
    const shots = [shot({ id: "a", strokesGained: -0.9 })];
    expect(computeReviewQueue(shots)).toEqual([{ type: "strike_quality", shotId: "a" }]);
  });

  it("reviews a shot's concerns one at a time, in priority order", () => {
    // a shot that both ended in a hazard AND has bad strokes gained
    const shots = [shot({ id: "a", endLie: "penalty", strokesGained: -1.2 })];
    const queue = computeReviewQueue(shots);
    expect(queue).toEqual([{ type: "penalty", shotId: "a" }]);
  });

  it("surfaces items across multiple shots independently", () => {
    const shots = [
      shot({ id: "a", endLie: "penalty" }),
      shot({ id: "b", strokesGained: -0.5 }),
    ];
    expect(computeReviewQueue(shots)).toEqual([
      { type: "penalty", shotId: "a" },
      { type: "strike_quality", shotId: "b" },
    ]);
  });
});

describe("applyPenaltyResolution", () => {
  it("matches the OB/lost-ball seed pattern (hole 2)", () => {
    const shots = [
      shot({
        id: "tee-shot", holeNumber: 2, shotNumber: 1, club: "Driver",
        startLie: "tee", endLie: "penalty", startDistanceYards: 385, endDistanceYards: 385,
      }),
      shot({
        id: "replay", holeNumber: 2, shotNumber: 2, club: "Driver",
        startLie: "tee", endLie: "fairway", startDistanceYards: 385, endDistanceYards: 150,
      }),
    ];

    const result = applyPenaltyResolution(shots, "tee-shot", "ob_lost_ball");

    expect(result).toHaveLength(3);
    expect(result[0]).toMatchObject({ id: "tee-shot", penaltyReviewed: true });
    expect(result[1]).toMatchObject({
      startLie: "penalty", endLie: "penalty",
      startDistanceYards: 385, endDistanceYards: 385,
      tag: "Penalty: Stroke & Distance", shotNumber: 2,
    });
    expect(result[2]).toMatchObject({ id: "replay", shotNumber: 3 });
  });

  it("matches the lateral hazard seed pattern (hole 14)", () => {
    const shots = [
      shot({
        id: "approach", holeNumber: 14, shotNumber: 1, club: "8-Iron",
        startLie: "fairway", endLie: "penalty", startDistanceYards: 140, endDistanceYards: 140,
      }),
    ];

    const result = applyPenaltyResolution(shots, "approach", "lateral_hazard");

    expect(result[1]).toMatchObject({
      startLie: "penalty", endLie: "penalty",
      startDistanceYards: 140, endDistanceYards: 140,
      tag: "Penalty: Lateral Hazard Drop", shotNumber: 2,
    });
  });

  it("only renumbers shots on the same hole", () => {
    const shots = [
      shot({ id: "a", holeNumber: 1, shotNumber: 1, endLie: "penalty" }),
      shot({ id: "b", holeNumber: 2, shotNumber: 1 }),
    ];

    const result = applyPenaltyResolution(shots, "a", "ob_lost_ball");

    const holeTwoShot = result.find((s) => s.id === "b");
    expect(holeTwoShot?.shotNumber).toBe(1);
  });
});

describe("applyFringeIsolationResolution", () => {
  it("reclassifies to green and marks reviewed", () => {
    const shots = [shot({ id: "a", club: "Putter", startLie: "fringe" })];
    const result = applyFringeIsolationResolution(shots, "a", "green");
    expect(result[0]).toMatchObject({ startLie: "green", fringeIsolationReviewed: true });
  });
});

describe("applyPuttRoutingResolution", () => {
  it("holes the putt when made", () => {
    const shots = [shot({ id: "a", club: "Putter", startLie: "green", endLie: "green" })];
    const result = applyPuttRoutingResolution(shots, "a", { made: true });
    expect(result[0]).toMatchObject({
      endLie: "hole", endDistanceYards: 0, puttRoutingReviewed: true,
      puttRouteResult: { made: true },
    });
  });

  it("leaves the lie/distance alone for a missed short putt", () => {
    const shots = [
      shot({ id: "a", club: "Putter", startLie: "green", endLie: "green", endDistanceYards: 0.3 }),
    ];
    const result = applyPuttRoutingResolution(shots, "a", { made: false });
    expect(result[0]).toMatchObject({ endLie: "green", endDistanceYards: 0.3 });
  });

  it("records lag proximity for a long putt without holing it", () => {
    const shots = [shot({ id: "a", club: "Putter", startLie: "green", endLie: "green" })];
    const result = applyPuttRoutingResolution(shots, "a", { lagProximityFeet: 2.5 });
    expect(result[0]).toMatchObject({
      puttRoutingReviewed: true,
      puttRouteResult: { lagProximityFeet: 2.5 },
      endLie: "green",
    });
  });
});

describe("applyStrikeQualityResolution", () => {
  it("sets the tag and marks reviewed", () => {
    const shots = [shot({ id: "a", strokesGained: -0.9 })];
    const result = applyStrikeQualityResolution(shots, "a", "Toe");
    expect(result[0]).toMatchObject({ tag: "Toe", strikeQualityReviewed: true });
  });
});

describe("markReviewed", () => {
  it.each([
    ["penalty", "penaltyReviewed"],
    ["fringe_isolation", "fringeIsolationReviewed"],
    ["putt_routing", "puttRoutingReviewed"],
    ["strike_quality", "strikeQualityReviewed"],
  ] as const)("marks %s reviewed via %s", (type, flag) => {
    const shots = [shot({ id: "a" })];
    const result = markReviewed(shots, "a", type);
    expect(result[0][flag]).toBe(true);
  });
});
