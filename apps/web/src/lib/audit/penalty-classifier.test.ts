import { describe, expect, it } from "vitest";
import { classifyPenaltyDrop, type PenaltyDropContext } from "./penalty-classifier";

describe("classifyPenaltyDrop", () => {
  // Mirrors apps/api/app/db/seed.py hole 2: a tee shot goes OB, and the
  // stroke-and-distance penalty replays from the tee at the same distance.
  it("routes OB/lost ball to a stroke-and-distance replay from the original spot", () => {
    const context: PenaltyDropContext = {
      precedingShotStartLie: "tee",
      precedingShotStartDistanceYards: 385,
      enteredHazardDistanceYards: 385,
    };

    const result = classifyPenaltyDrop("ob_lost_ball", context);

    expect(result).toEqual({
      penaltyType: "ob_lost_ball",
      dropLie: "tee",
      dropDistanceYards: 385,
      tag: "Penalty: Stroke & Distance",
    });
  });

  // Mirrors apps/api/app/db/seed.py hole 14: an approach shot finds a water
  // hazard from 140y, and the lateral-hazard drop keeps the distance to the
  // hole roughly unchanged (dropped near the entry point).
  it("routes lateral hazard to a drop near the entry point, distance unchanged", () => {
    const context: PenaltyDropContext = {
      precedingShotStartLie: "fairway",
      precedingShotStartDistanceYards: 140,
      enteredHazardDistanceYards: 140,
    };

    const result = classifyPenaltyDrop("lateral_hazard", context);

    expect(result).toEqual({
      penaltyType: "lateral_hazard",
      dropLie: "rough",
      dropDistanceYards: 140,
      tag: "Penalty: Lateral Hazard Drop",
    });
  });

  it("OB replay ignores where the ball was lost, only cares about the original spot", () => {
    const context: PenaltyDropContext = {
      precedingShotStartLie: "fairway",
      precedingShotStartDistanceYards: 210,
      enteredHazardDistanceYards: 40, // ball was nearly at the green when lost
    };

    const result = classifyPenaltyDrop("ob_lost_ball", context);

    expect(result.dropDistanceYards).toBe(210);
    expect(result.dropLie).toBe("fairway");
  });

  it("lateral hazard drop ignores the original spot, only cares about the entry point", () => {
    const context: PenaltyDropContext = {
      precedingShotStartLie: "tee",
      precedingShotStartDistanceYards: 400,
      enteredHazardDistanceYards: 165,
    };

    const result = classifyPenaltyDrop("lateral_hazard", context);

    expect(result.dropDistanceYards).toBe(165);
    expect(result.dropLie).not.toBe("tee");
  });
});
