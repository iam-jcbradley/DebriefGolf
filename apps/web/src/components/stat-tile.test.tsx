import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatTile } from "./stat-tile";

describe("StatTile", () => {
  it("renders the label and value", () => {
    render(<StatTile label="SG: Putting" value="+0.58" />);
    expect(screen.getByText("SG: Putting")).toBeInTheDocument();
    expect(screen.getByText("+0.58")).toBeInTheDocument();
  });

  it("renders optional detail text", () => {
    render(<StatTile label="SG: Putting" value="-1.15" detail="Lag proximity: 4.8ft" />);
    expect(screen.getByText("Lag proximity: 4.8ft")).toBeInTheDocument();
  });

  it("shows an up indicator for a good tone", () => {
    render(<StatTile label="SG: OTT" value="+1.20" tone="good" />);
    expect(screen.getByText("↑", { exact: false })).toBeInTheDocument();
  });

  it("shows a down indicator for a bad tone", () => {
    render(<StatTile label="SG: APP" value="-2.40" tone="bad" />);
    expect(screen.getByText("↓", { exact: false })).toBeInTheDocument();
  });

  it("shows no directional indicator for a neutral tone", () => {
    render(<StatTile label="Par 5 Bogeys" value="0" tone="neutral" />);
    expect(screen.queryByText("↑", { exact: false })).not.toBeInTheDocument();
    expect(screen.queryByText("↓", { exact: false })).not.toBeInTheDocument();
  });

  it("shows a checkmark, not an up arrow, for a good status count", () => {
    render(<StatTile label="Blown Recoveries" value="0" tone="good" indicator="status" />);
    expect(screen.getByText("✓", { exact: false })).toBeInTheDocument();
    expect(screen.queryByText("↑", { exact: false })).not.toBeInTheDocument();
  });

  it("shows a warning glyph, not a down arrow, for a bad status count", () => {
    render(<StatTile label="Doubles+" value="1" tone="bad" indicator="status" />);
    expect(screen.getByText("⚠", { exact: false })).toBeInTheDocument();
    expect(screen.queryByText("↓", { exact: false })).not.toBeInTheDocument();
  });
});
