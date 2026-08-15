import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Overline } from "./overline";

describe("Overline", () => {
  it("renders its children", () => {
    render(<Overline>Round Summary</Overline>);
    expect(screen.getByText("Round Summary")).toBeInTheDocument();
  });

  it("renders as a <p> by default", () => {
    const { container } = render(<Overline>Label</Overline>);
    expect(container.querySelector("p")).not.toBeNull();
  });

  it("renders as a different element when `as` is given", () => {
    const { container } = render(<Overline as="span">Label</Overline>);
    expect(container.querySelector("span")).not.toBeNull();
    expect(container.querySelector("p")).toBeNull();
  });

  it("applies the accent color when accent is set", () => {
    render(<Overline accent>Label</Overline>);
    expect(screen.getByText("Label")).toHaveClass("text-primary");
  });
});
