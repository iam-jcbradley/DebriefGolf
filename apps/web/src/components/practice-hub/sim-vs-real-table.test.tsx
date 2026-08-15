import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SimVsRealGapping } from "@/lib/api";
import { SimVsRealTable } from "./sim-vs-real-table";

describe("SimVsRealTable", () => {
  it("shows an empty state with no rows", () => {
    render(<SimVsRealTable rows={[]} />);
    expect(screen.getByText(/needs both/i)).toBeInTheDocument();
  });

  it("renders the delta with a leading sign", () => {
    const rows: SimVsRealGapping[] = [
      { club: "Driver", range_carry_mean_yards: 260, on_course_carry_mean_yards: 245, delta_yards: 15 },
    ];
    render(<SimVsRealTable rows={rows} />);
    expect(screen.getByText("+15y")).toBeInTheDocument();
  });

  it("renders a dash when the delta can't be computed", () => {
    const rows: SimVsRealGapping[] = [
      { club: "Driver", range_carry_mean_yards: 260, on_course_carry_mean_yards: null, delta_yards: null },
    ];
    render(<SimVsRealTable rows={rows} />);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});
