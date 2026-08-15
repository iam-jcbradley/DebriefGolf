import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HoleGeometryEditor, type HoleGeometryValue } from "./hole-geometry-editor";

vi.mock("mapbox-gl/dist/mapbox-gl.css", () => ({}));
vi.mock("mapbox-gl", () => ({
  default: { accessToken: "", Map: vi.fn(), Marker: vi.fn() },
}));

const CENTER = { lat: 33.7, lng: -78.9 };
const EMPTY: HoleGeometryValue = { tee_location: null, green_center: null, green_boundary: null };

beforeEach(() => {
  Element.prototype.getBoundingClientRect = vi.fn(() => ({
    left: 0, top: 0, width: 400, height: 400, right: 400, bottom: 400, x: 0, y: 0,
    toJSON: () => {},
  }));
});

describe("HoleGeometryEditor", () => {
  it("defaults to tee placement mode and sets tee_location on click", () => {
    const onChange = vi.fn();
    render(<HoleGeometryEditor center={CENTER} value={EMPTY} onChange={onChange} />);

    fireEvent.click(screen.getByRole("img"), { clientX: 200, clientY: 200 });

    expect(onChange).toHaveBeenCalledTimes(1);
    const updated = onChange.mock.calls[0][0] as HoleGeometryValue;
    expect(updated.tee_location).not.toBeNull();
    expect(updated.green_center).toBeNull();
  });

  it("switches to green mode and sets green_center instead of tee_location", () => {
    const onChange = vi.fn();
    render(<HoleGeometryEditor center={CENTER} value={EMPTY} onChange={onChange} />);

    fireEvent.click(screen.getByRole("radio", { name: "green" }));
    fireEvent.click(screen.getByRole("img"), { clientX: 200, clientY: 200 });

    const updated = onChange.mock.calls[0][0] as HoleGeometryValue;
    expect(updated.green_center).not.toBeNull();
    expect(updated.tee_location).toBeNull();
  });

  it("appends boundary points instead of replacing them", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <HoleGeometryEditor center={CENTER} value={EMPTY} onChange={onChange} />
    );

    fireEvent.click(screen.getByRole("radio", { name: "Green boundary" }));
    fireEvent.click(screen.getByRole("img"), { clientX: 200, clientY: 200 });
    const afterFirst = onChange.mock.calls[0][0] as HoleGeometryValue;
    expect(afterFirst.green_boundary).toHaveLength(1);

    rerender(<HoleGeometryEditor center={CENTER} value={afterFirst} onChange={onChange} />);
    fireEvent.click(screen.getByRole("img"), { clientX: 250, clientY: 200 });
    const afterSecond = onChange.mock.calls[1][0] as HoleGeometryValue;
    expect(afterSecond.green_boundary).toHaveLength(2);
  });

  it("clears the boundary when the clear button is clicked", () => {
    const onChange = vi.fn();
    const withBoundary: HoleGeometryValue = {
      ...EMPTY,
      green_boundary: [{ lat: 33.7001, lng: -78.9 }],
    };
    render(<HoleGeometryEditor center={CENTER} value={withBoundary} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Clear boundary" }));

    expect(onChange).toHaveBeenCalledWith({ ...withBoundary, green_boundary: [] });
  });

  it("does not show the clear-boundary button with no boundary points", () => {
    render(<HoleGeometryEditor center={CENTER} value={EMPTY} onChange={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Clear boundary" })).not.toBeInTheDocument();
  });
});
