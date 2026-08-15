import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { VirtualRound } from "@/lib/api";
import { VirtualRoundList } from "./virtual-round-list";

const round: VirtualRound = {
  id: 1,
  user_id: 1,
  platform: "gspro",
  course_name: "TPC Sawgrass",
  played_at: "2026-08-10T00:00:00Z",
  holes_played: 18,
  total_score: 82,
  notes: null,
};

describe("VirtualRoundList", () => {
  it("shows an empty state with no rounds", () => {
    render(<VirtualRoundList rounds={[]} />);
    expect(screen.getByText(/no virtual rounds logged yet/i)).toBeInTheDocument();
  });

  it("renders the course, platform label, and score", () => {
    render(<VirtualRoundList rounds={[round]} />);
    expect(screen.getByText("TPC Sawgrass")).toBeInTheDocument();
    expect(screen.getByText(/GSPro/)).toBeInTheDocument();
    expect(screen.getByText("82")).toBeInTheDocument();
  });

  it("renders a dash when there is no score", () => {
    render(<VirtualRoundList rounds={[{ ...round, total_score: null }]} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
