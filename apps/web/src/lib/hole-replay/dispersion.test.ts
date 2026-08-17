import { describe, expect, it } from "vitest";
import type { DispersionEllipse } from "@/lib/api";
import { isWithinEllipse } from "./dispersion";

function ellipse(overrides: Partial<DispersionEllipse> = {}): DispersionEllipse {
  return {
    center_longitudinal_yards: 150.0,
    center_lateral_yards: 0.0,
    semi_major_yards: 10.0,
    semi_minor_yards: 5.0,
    k: 1.0,
    ...overrides,
  };
}

describe("isWithinEllipse", () => {
  it("contains the center point", () => {
    expect(isWithinEllipse(ellipse(), 150.0, 0.0)).toBe(true);
  });

  it("contains a point exactly on the major-axis boundary", () => {
    expect(isWithinEllipse(ellipse(), 160.0, 0.0)).toBe(true);
  });

  it("excludes a point just past the major-axis boundary", () => {
    expect(isWithinEllipse(ellipse(), 160.01, 0.0)).toBe(false);
  });

  it("contains a point exactly on the minor-axis boundary", () => {
    expect(isWithinEllipse(ellipse(), 150.0, 5.0)).toBe(true);
  });

  it("contains a diagonal point exactly on the boundary", () => {
    // semi_major=4, semi_minor=3; (4*0.6, 3*0.8) satisfies 0.6^2+0.8^2=1 exactly.
    const e = ellipse({ center_longitudinal_yards: 0, semi_major_yards: 4, semi_minor_yards: 3 });
    expect(isWithinEllipse(e, 2.4, 2.4)).toBe(true);
  });

  it("excludes a diagonal point outside the boundary", () => {
    const e = ellipse({ center_longitudinal_yards: 0, semi_major_yards: 4, semi_minor_yards: 3 });
    expect(isWithinEllipse(e, 3.0, 3.0)).toBe(false);
  });

  it("treats a degenerate (zero-stdev) ellipse as containing only its center", () => {
    const e = ellipse({ semi_major_yards: 0, semi_minor_yards: 0 });
    expect(isWithinEllipse(e, 150.0, 0.0)).toBe(true);
    expect(isWithinEllipse(e, 150.1, 0.0)).toBe(false);
  });
});
