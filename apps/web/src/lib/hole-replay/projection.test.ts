import { describe, expect, it } from "vitest";
import { localYards, offsetFromAimLine, type LatLng } from "./projection";

const YARDS_PER_DEGREE_LAT = 121_000.0;
const TEE: LatLng = { lat: 0, lng: 0 };

function green(yardage: number): LatLng {
  return { lat: yardage / YARDS_PER_DEGREE_LAT, lng: 0 };
}

describe("localYards", () => {
  it("is zero at the origin", () => {
    const { east, north } = localYards(TEE, TEE);
    expect(east).toBeCloseTo(0);
    expect(north).toBeCloseTo(0);
  });

  it("converts a north offset", () => {
    const { east, north } = localYards(TEE, { lat: 100 / YARDS_PER_DEGREE_LAT, lng: 0 });
    expect(north).toBeCloseTo(100);
    expect(east).toBeCloseTo(0);
  });

  it("converts an east offset", () => {
    const { east, north } = localYards(TEE, { lat: 0, lng: 50 / YARDS_PER_DEGREE_LAT });
    expect(east).toBeCloseTo(50);
    expect(north).toBeCloseTo(0);
  });
});

describe("offsetFromAimLine", () => {
  it("places the green at full longitudinal, zero lateral", () => {
    const g = green(400);
    const offset = offsetFromAimLine(TEE, g, g);
    expect(offset.longitudinalYards).toBeCloseTo(400);
    expect(offset.lateralYards).toBeCloseTo(0);
  });

  it("places the tee at zero both ways", () => {
    const offset = offsetFromAimLine(TEE, green(400), TEE);
    expect(offset.longitudinalYards).toBeCloseTo(0);
    expect(offset.lateralYards).toBeCloseTo(0);
  });

  it("gives a positive lateral offset to the right of the aim line", () => {
    const point = { lat: 200 / YARDS_PER_DEGREE_LAT, lng: 15 / YARDS_PER_DEGREE_LAT };
    const offset = offsetFromAimLine(TEE, green(400), point);
    expect(offset.longitudinalYards).toBeCloseTo(200);
    expect(offset.lateralYards).toBeCloseTo(15);
  });

  it("gives a negative lateral offset to the left of the aim line", () => {
    const point = { lat: 200 / YARDS_PER_DEGREE_LAT, lng: -15 / YARDS_PER_DEGREE_LAT };
    const offset = offsetFromAimLine(TEE, green(400), point);
    expect(offset.lateralYards).toBeCloseTo(-15);
  });

  it("throws when tee and green coincide", () => {
    expect(() => offsetFromAimLine(TEE, TEE, TEE)).toThrow(/coincide/);
  });
});
