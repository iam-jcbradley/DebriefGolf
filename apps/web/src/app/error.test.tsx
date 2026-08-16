import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders as render } from "@/lib/test-utils";
// Aliased: importing this as `Error` would shadow the global `Error`
// constructor in this file, and `new Error("boom")` below would try to
// construct the React component instead of a real error.
import ErrorBoundary from "./error";

describe("Error", () => {
  it("shows a recoverable message instead of a whitescreen", () => {
    render(<ErrorBoundary error={new Error("boom")} reset={vi.fn()} />);

    expect(screen.getByText("This page hit an unexpected error")).toBeInTheDocument();
  });

  it("calls reset when 'Try again' is clicked", async () => {
    const reset = vi.fn();
    render(<ErrorBoundary error={new Error("boom")} reset={reset} />);

    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(reset).toHaveBeenCalledOnce();
  });

  it("links back to the dashboard", () => {
    render(<ErrorBoundary error={new Error("boom")} reset={vi.fn()} />);

    expect(screen.getByRole("link", { name: "Back to dashboard" })).toHaveAttribute("href", "/");
  });
});
