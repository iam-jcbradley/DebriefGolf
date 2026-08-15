import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RoundAnalytics } from "@/lib/api";
import { TigerFiveMeter } from "./tiger-five-meter";

const tigerFive: RoundAnalytics["tiger_five"] = {
  double_bogeys_or_worse: 1,
  three_putts: 2,
  par_five_bogeys: 0,
  blown_recoveries_inside_50: 0,
  penalties_inside_150: 1,
  clean_card_index: 66.7,
};

describe("TigerFiveMeter", () => {
  it("renders all five violation counts", () => {
    render(<TigerFiveMeter tigerFive={tigerFive} />);
    expect(screen.getByText("Doubles+")).toBeInTheDocument();
    expect(screen.getByText("3-Putts")).toBeInTheDocument();
    expect(screen.getByText("Par 5 Bogeys")).toBeInTheDocument();
    expect(screen.getByText("Blown Recoveries")).toBeInTheDocument();
    expect(screen.getByText("Penalties Inside 150y")).toBeInTheDocument();
  });

  it("renders the Clean Card Index as a meter with the correct value", () => {
    render(<TigerFiveMeter tigerFive={tigerFive} />);
    const meter = screen.getByRole("meter", { name: "Clean Card Index" });
    expect(meter).toHaveAttribute("aria-valuenow", "66.7");
    expect(screen.getByText("66.7%")).toBeInTheDocument();
  });

  it("shows a zero-count violation with a checkmark, not a down arrow", () => {
    render(<TigerFiveMeter tigerFive={tigerFive} />);
    const blownRecoveriesTile = screen.getByText("Blown Recoveries").closest("div");
    expect(blownRecoveriesTile?.textContent).toContain("✓");
    expect(blownRecoveriesTile?.textContent).not.toContain("↓");
  });

  it("shows a non-zero violation count with a warning glyph, not an up arrow", () => {
    render(<TigerFiveMeter tigerFive={tigerFive} />);
    const doublesTile = screen.getByText("Doubles+").closest("div");
    expect(doublesTile?.textContent).toContain("⚠");
    expect(doublesTile?.textContent).not.toContain("↑");
  });
});
