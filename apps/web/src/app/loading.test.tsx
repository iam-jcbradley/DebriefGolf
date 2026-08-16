import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithProviders as render } from "@/lib/test-utils";
import Loading from "./loading";

describe("Loading", () => {
  it("shows a loading message", () => {
    render(<Loading />);

    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });
});
