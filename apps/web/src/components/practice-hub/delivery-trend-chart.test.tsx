import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DeliveryTrendPoint } from "@/lib/api";
import { DeliveryTrendChart } from "./delivery-trend-chart";

function point(overrides: Partial<DeliveryTrendPoint>): DeliveryTrendPoint {
  return {
    session_id: 1,
    recorded_at: "2026-01-01T00:00:00Z",
    shot_count: 5,
    avg_carry_yards: 250,
    avg_smash_factor: 1.4,
    avg_face_to_path_deg: 1.0,
    avg_spin_axis_deg: -1.0,
    ...overrides,
  };
}

describe("DeliveryTrendChart", () => {
  it("shows a message instead of a chart with fewer than two sessions", () => {
    render(<DeliveryTrendChart club="Driver" points={[point({})]} />);
    expect(screen.getByText(/need at least two driver sessions/i)).toBeInTheDocument();
  });

  it("renders a chart with two or more sessions", () => {
    const points = [
      point({ session_id: 1, recorded_at: "2026-01-01T00:00:00Z" }),
      point({ session_id: 2, recorded_at: "2026-02-01T00:00:00Z" }),
    ];
    render(<DeliveryTrendChart club="Driver" points={points} />);
    expect(screen.getByRole("img", { name: /driver smash factor trend/i })).toBeInTheDocument();
  });
});
