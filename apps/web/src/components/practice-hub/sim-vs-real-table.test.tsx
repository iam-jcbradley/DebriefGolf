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

  it("shows the empty state, not an all-dash table, when rows exist but none have range data", () => {
    // On-course clubs exist as soon as a round is logged, independent of
    // whether any R10/R50 session ever ran — this is the shape `rows`
    // takes for a golfer with zero launch monitor data.
    const rows: SimVsRealGapping[] = [
      { club: "Driver", range_carry_mean_yards: null, on_course_carry_mean_yards: 245, delta_yards: null },
      { club: "7-Iron", range_carry_mean_yards: null, on_course_carry_mean_yards: 150, delta_yards: null },
    ];
    render(<SimVsRealTable rows={rows} />);
    expect(screen.getByText(/needs both/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("still renders the table when only some rows have range data", () => {
    const rows: SimVsRealGapping[] = [
      { club: "Driver", range_carry_mean_yards: 260, on_course_carry_mean_yards: 245, delta_yards: 15 },
      { club: "7-Iron", range_carry_mean_yards: null, on_course_carry_mean_yards: 150, delta_yards: null },
    ];
    render(<SimVsRealTable rows={rows} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("+15y")).toBeInTheDocument();
  });
});
