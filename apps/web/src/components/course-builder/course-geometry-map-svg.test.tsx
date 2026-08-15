import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CourseGeometryMapSvg } from "./course-geometry-map-svg";

const CENTER = { lat: 33.7, lng: -78.9 };

beforeEach(() => {
  // jsdom doesn't do layout — mock a rect matching the SVG's own
  // width/height so client coordinates map 1:1 onto the view.
  Element.prototype.getBoundingClientRect = vi.fn(() => ({
    left: 0,
    top: 0,
    width: 400,
    height: 400,
    right: 400,
    bottom: 400,
    x: 0,
    y: 0,
    toJSON: () => {},
  }));
});

describe("CourseGeometryMapSvg", () => {
  it("renders an accessible svg", () => {
    render(
      <CourseGeometryMapSvg center={CENTER} tee={null} green={null} boundary={[]} onPick={vi.fn()} />
    );
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("renders a tee marker when tee is set", () => {
    const { container } = render(
      <CourseGeometryMapSvg center={CENTER} tee={CENTER} green={null} boundary={[]} onPick={vi.fn()} />
    );
    expect(container.querySelector('[data-testid="tee-point"]')).not.toBeNull();
  });

  it("renders a green marker when green is set", () => {
    const { container } = render(
      <CourseGeometryMapSvg center={CENTER} tee={null} green={CENTER} boundary={[]} onPick={vi.fn()} />
    );
    expect(container.querySelector('[data-testid="green-point"]')).not.toBeNull();
  });

  it("renders a boundary polygon once at least 3 points are placed", () => {
    const boundary = [
      { lat: 33.7001, lng: -78.9 },
      { lat: 33.7001, lng: -78.8999 },
      { lat: 33.7, lng: -78.8999 },
    ];
    const { container } = render(
      <CourseGeometryMapSvg center={CENTER} tee={null} green={null} boundary={boundary} onPick={vi.fn()} />
    );
    expect(container.querySelector('[data-testid="green-boundary-polygon"]')).not.toBeNull();
    expect(container.querySelectorAll('[data-testid="boundary-point"]')).toHaveLength(3);
  });

  it("omits the polygon with fewer than 3 boundary points", () => {
    const { container } = render(
      <CourseGeometryMapSvg
        center={CENTER}
        tee={null}
        green={null}
        boundary={[{ lat: 33.7001, lng: -78.9 }]}
        onPick={vi.fn()}
      />
    );
    expect(container.querySelector('[data-testid="green-boundary-polygon"]')).toBeNull();
  });

  it("calls onPick with the clicked point's lat/lng", () => {
    const onPick = vi.fn();
    render(
      <CourseGeometryMapSvg center={CENTER} tee={null} green={null} boundary={[]} onPick={onPick} />
    );
    fireEvent.click(screen.getByRole("img"), { clientX: 200, clientY: 200 }); // dead center

    expect(onPick).toHaveBeenCalledTimes(1);
    const [{ lat, lng }] = onPick.mock.calls[0];
    expect(lat).toBeCloseTo(CENTER.lat, 4);
    expect(lng).toBeCloseTo(CENTER.lng, 4);
  });

  it("calls onPick with a point east of center for a rightward click", () => {
    const onPick = vi.fn();
    render(
      <CourseGeometryMapSvg center={CENTER} tee={null} green={null} boundary={[]} onPick={onPick} />
    );
    fireEvent.click(screen.getByRole("img"), { clientX: 300, clientY: 200 });

    const [{ lng }] = onPick.mock.calls[0];
    expect(lng).toBeGreaterThan(CENTER.lng);
  });
});
