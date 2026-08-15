import { describe, expect, it } from "vitest";
import { latLngToLocalPoint, localPointToLatLng } from "./local-map";

const CENTER = { lat: 33.7, lng: -78.9 };
const view = { width: 400, height: 400, yardsPerPixel: 2 };

describe("latLngToLocalPoint", () => {
  it("places the center at the middle of the view", () => {
    const point = latLngToLocalPoint(CENTER, CENTER, view);
    expect(point.x).toBeCloseTo(view.width / 2);
    expect(point.y).toBeCloseTo(view.height / 2);
  });

  it("moves right for a point east of center", () => {
    const point = latLngToLocalPoint(CENTER, { lat: CENTER.lat, lng: CENTER.lng + 0.001 }, view);
    expect(point.x).toBeGreaterThan(view.width / 2);
  });

  it("moves up (smaller y) for a point north of center", () => {
    const point = latLngToLocalPoint(CENTER, { lat: CENTER.lat + 0.001, lng: CENTER.lng }, view);
    expect(point.y).toBeLessThan(view.height / 2);
  });
});

describe("localPointToLatLng", () => {
  it("round-trips the center point", () => {
    const point = latLngToLocalPoint(CENTER, CENTER, view);
    const recovered = localPointToLatLng(CENTER, point, view);
    expect(recovered.lat).toBeCloseTo(CENTER.lat);
    expect(recovered.lng).toBeCloseTo(CENTER.lng);
  });

  it("round-trips an arbitrary off-center point", () => {
    const original = { lat: 33.7025, lng: -78.9015 };
    const point = latLngToLocalPoint(CENTER, original, view);
    const recovered = localPointToLatLng(CENTER, point, view);
    expect(recovered.lat).toBeCloseTo(original.lat, 9);
    expect(recovered.lng).toBeCloseTo(original.lng, 9);
  });

  it("recovers a rightward click as east of center", () => {
    const point = { x: view.width / 2 + 50, y: view.height / 2 };
    const recovered = localPointToLatLng(CENTER, point, view);
    expect(recovered.lng).toBeGreaterThan(CENTER.lng);
  });
});
