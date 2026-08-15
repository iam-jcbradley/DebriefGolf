import { describe, expect, it } from "vitest";
import { svgPointToOffset, yardsToSvgLength, yardsToSvgPoint } from "./coordinates";

const viewBox = { width: 200, height: 400, paddingYards: 20 };
const holeYardage = 400;
// totalYards = 440, scale = 400 / 440 = 0.90909...

describe("yardsToSvgPoint", () => {
  it("places the tee (longitudinal 0) near the bottom of the view", () => {
    const point = yardsToSvgPoint({ longitudinalYards: 0, lateralYards: 0 }, holeYardage, viewBox);
    const scale = viewBox.height / (holeYardage + viewBox.paddingYards * 2);
    expect(point.y).toBeCloseTo(viewBox.height - viewBox.paddingYards * scale);
    expect(point.x).toBeCloseTo(viewBox.width / 2);
  });

  it("places the green (longitudinal = hole yardage) above the tee", () => {
    const tee = yardsToSvgPoint({ longitudinalYards: 0, lateralYards: 0 }, holeYardage, viewBox);
    const green = yardsToSvgPoint(
      { longitudinalYards: holeYardage, lateralYards: 0 },
      holeYardage,
      viewBox
    );
    expect(green.y).toBeLessThan(tee.y); // smaller SVG y = higher on screen
  });

  it("centers zero lateral offset horizontally", () => {
    const point = yardsToSvgPoint(
      { longitudinalYards: 150, lateralYards: 0 },
      holeYardage,
      viewBox
    );
    expect(point.x).toBeCloseTo(viewBox.width / 2);
  });

  it("moves right for a positive lateral offset", () => {
    const point = yardsToSvgPoint(
      { longitudinalYards: 150, lateralYards: 10 },
      holeYardage,
      viewBox
    );
    expect(point.x).toBeGreaterThan(viewBox.width / 2);
  });

  it("moves left for a negative lateral offset", () => {
    const point = yardsToSvgPoint(
      { longitudinalYards: 150, lateralYards: -10 },
      holeYardage,
      viewBox
    );
    expect(point.x).toBeLessThan(viewBox.width / 2);
  });
});

describe("yardsToSvgLength", () => {
  it("scales a yard distance by the same factor as the point transform", () => {
    const scale = viewBox.height / (holeYardage + viewBox.paddingYards * 2);
    expect(yardsToSvgLength(10, holeYardage, viewBox)).toBeCloseTo(10 * scale);
  });

  it("returns zero for zero yards", () => {
    expect(yardsToSvgLength(0, holeYardage, viewBox)).toBe(0);
  });
});

describe("svgPointToOffset", () => {
  it("round-trips an arbitrary offset through yardsToSvgPoint and back", () => {
    const original = { longitudinalYards: 150, lateralYards: 10 };
    const point = yardsToSvgPoint(original, holeYardage, viewBox);
    const recovered = svgPointToOffset(point, holeYardage, viewBox);
    expect(recovered.longitudinalYards).toBeCloseTo(original.longitudinalYards);
    expect(recovered.lateralYards).toBeCloseTo(original.lateralYards);
  });

  it("recovers zero offset at the tee's own SVG point", () => {
    const tee = yardsToSvgPoint({ longitudinalYards: 0, lateralYards: 0 }, holeYardage, viewBox);
    const recovered = svgPointToOffset(tee, holeYardage, viewBox);
    expect(recovered.longitudinalYards).toBeCloseTo(0);
    expect(recovered.lateralYards).toBeCloseTo(0);
  });

  it("recovers a rightward click as a positive lateral offset", () => {
    const point = { x: viewBox.width / 2 + 20, y: viewBox.height / 2 };
    const recovered = svgPointToOffset(point, holeYardage, viewBox);
    expect(recovered.lateralYards).toBeGreaterThan(0);
  });
});
