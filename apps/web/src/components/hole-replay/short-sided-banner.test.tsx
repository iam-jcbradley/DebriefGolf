import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ShortSidedBanner } from "./short-sided-banner";

describe("ShortSidedBanner", () => {
  it("renders nothing when there are no short-sided misses", () => {
    const { container } = render(<ShortSidedBanner holeNumber={7} shortSidedCount={0} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a singular message for exactly one short-sided miss", () => {
    render(<ShortSidedBanner holeNumber={7} shortSidedCount={1} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Short-sided miss on hole 7");
    expect(alert).toHaveTextContent("1 approach shot left a tight up-and-down");
  });

  it("pluralizes for more than one short-sided miss", () => {
    render(<ShortSidedBanner holeNumber={12} shortSidedCount={2} />);
    expect(screen.getByRole("alert")).toHaveTextContent("2 approach shots left a tight");
  });
});
