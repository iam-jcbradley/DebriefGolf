import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithProviders as render } from "@/lib/test-utils";
import NotFound from "./not-found";

describe("NotFound", () => {
  it("shows a styled 404 with a way back", () => {
    render(<NotFound />);

    expect(screen.getByText("This page doesn't exist")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to dashboard" })).toHaveAttribute("href", "/");
  });
});
