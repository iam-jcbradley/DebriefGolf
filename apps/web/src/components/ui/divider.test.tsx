import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Divider } from "./divider";

describe("Divider", () => {
  it("renders as a horizontal separator", () => {
    render(<Divider />);
    expect(screen.getByRole("separator")).toBeInTheDocument();
  });

  it("shows a star glyph by default", () => {
    render(<Divider />);
    expect(screen.getByText("✦")).toBeInTheDocument();
  });

  it("shows a dot glyph when requested", () => {
    render(<Divider glyph="dot" />);
    expect(screen.getByText("•")).toBeInTheDocument();
  });
});
