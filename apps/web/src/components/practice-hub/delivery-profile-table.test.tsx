import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ClubDeliveryProfile } from "@/lib/api";
import { DeliveryProfileTable } from "./delivery-profile-table";

const clubs: ClubDeliveryProfile[] = [
  {
    club: "Driver",
    shot_count: 10,
    avg_club_path_deg: -1.2,
    avg_face_angle_deg: 0.5,
    avg_face_to_path_deg: 1.7,
    avg_spin_axis_deg: -2.1,
    avg_smash_factor: 1.48,
    avg_carry_yards: 255.4,
  },
];

describe("DeliveryProfileTable", () => {
  it("shows an empty state with no clubs", () => {
    render(<DeliveryProfileTable clubs={[]} />);
    expect(screen.getByText(/no launch monitor sessions/i)).toBeInTheDocument();
  });

  it("renders a row per club with its delivery numbers", () => {
    render(<DeliveryProfileTable clubs={clubs} />);
    expect(screen.getByText("Driver")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("1.48")).toBeInTheDocument();
    expect(screen.getByText("255.4y")).toBeInTheDocument();
  });

  it("renders a dash for missing values", () => {
    render(
      <DeliveryProfileTable
        clubs={[{ ...clubs[0], avg_carry_yards: null, avg_smash_factor: null }]}
      />
    );
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});
