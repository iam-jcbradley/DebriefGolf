import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DispersionEllipseOverlay } from "./dispersion-ellipse-overlay";

function renderInSvg(children: React.ReactNode) {
  return render(<svg>{children}</svg>);
}

describe("DispersionEllipseOverlay", () => {
  it("renders an ellipse with the given center and radii", () => {
    const { container } = renderInSvg(
      <DispersionEllipseOverlay centerX={100} centerY={50} radiusX={30} radiusY={12} />
    );
    const ellipse = container.querySelector("ellipse");
    expect(ellipse).not.toBeNull();
    expect(ellipse).toHaveAttribute("cx", "100");
    expect(ellipse).toHaveAttribute("cy", "50");
    expect(ellipse).toHaveAttribute("rx", "30");
    expect(ellipse).toHaveAttribute("ry", "12");
  });

  it("renders no label text by default", () => {
    const { container } = renderInSvg(
      <DispersionEllipseOverlay centerX={0} centerY={0} radiusX={10} radiusY={5} />
    );
    expect(container.querySelector("text")).toBeNull();
  });

  it("renders a label above the ellipse when given", () => {
    const { container, getByText } = renderInSvg(
      <DispersionEllipseOverlay centerX={0} centerY={0} radiusX={10} radiusY={5} label="7-Iron" />
    );
    expect(getByText("7-Iron")).toBeInTheDocument();
    const text = container.querySelector("text");
    expect(Number(text?.getAttribute("y"))).toBeLessThan(0); // above the ellipse's top edge
  });
});
