import { describe, expect, it } from "vitest";
import { STRIKE_QUALITY_SG_THRESHOLD, needsStrikeQualityTag } from "./strike-quality";

describe("needsStrikeQualityTag", () => {
  it("needs a tag when strokes gained is worse than the threshold", () => {
    expect(needsStrikeQualityTag(STRIKE_QUALITY_SG_THRESHOLD - 0.01)).toBe(true);
    expect(needsStrikeQualityTag(-1.2)).toBe(true);
  });

  it("does not need a tag exactly at the threshold", () => {
    expect(needsStrikeQualityTag(STRIKE_QUALITY_SG_THRESHOLD)).toBe(false);
  });

  it("does not need a tag for a mildly negative or positive shot", () => {
    expect(needsStrikeQualityTag(-0.1)).toBe(false);
    expect(needsStrikeQualityTag(0.5)).toBe(false);
  });

  it("does not need a tag when strokes gained hasn't been computed yet", () => {
    expect(needsStrikeQualityTag(undefined)).toBe(false);
  });
});
