import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PinProvenanceNote } from "./pin-provenance-note";

describe("PinProvenanceNote", () => {
  it("renders nothing once both a pin and a green boundary are recorded", () => {
    const { container } = render(<PinProvenanceNote hasPin={true} hasGreenBoundary={true} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("discloses the green-center fallback when no pin is recorded", () => {
    render(<PinProvenanceNote hasPin={false} hasGreenBoundary={true} />);
    const note = screen.getByText("Based on green center — no pin recorded");
    expect(note).toHaveClass("text-muted-foreground");
    expect(note).not.toHaveClass("text-status-critical");
  });

  it("discloses the distance fallback when a pin exists but no green boundary does", () => {
    render(<PinProvenanceNote hasPin={true} hasGreenBoundary={false} />);
    expect(screen.getByText("Based on distance — no green boundary recorded")).toBeInTheDocument();
  });

  it("leads with the pin-missing message when both are missing", () => {
    render(<PinProvenanceNote hasPin={false} hasGreenBoundary={false} />);
    expect(screen.getByText("Based on green center — no pin recorded")).toBeInTheDocument();
  });
});
