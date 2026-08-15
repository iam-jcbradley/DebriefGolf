import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DashboardPage from "./page";

describe("DashboardPage", () => {
  it("renders the Debrief Golf placeholder dashboard", () => {
    render(<DashboardPage />);
    expect(
      screen.getByRole("heading", { name: "Debrief Golf" })
    ).toBeInTheDocument();
    expect(screen.getByText("Rounds")).toBeInTheDocument();
  });
});
