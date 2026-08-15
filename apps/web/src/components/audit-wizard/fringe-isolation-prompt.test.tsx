import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FringeIsolationPrompt } from "./fringe-isolation-prompt";

describe("FringeIsolationPrompt", () => {
  it("renders nothing when the putt was on the green", () => {
    const { container } = render(
      <FringeIsolationPrompt club="Putter" startLie="green" onResolved={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing for a non-putter club", () => {
    const { container } = render(
      <FringeIsolationPrompt club="SW" startLie="fringe" onResolved={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("prompts when a putter is used from the fringe", () => {
    render(<FringeIsolationPrompt club="Putter" startLie="fringe" onResolved={vi.fn()} />);
    expect(screen.getByText("Was this putt actually on the green?")).toBeInTheDocument();
  });

  it("resolves to green when counted as a true putt", async () => {
    const onResolved = vi.fn();
    const user = userEvent.setup();
    render(<FringeIsolationPrompt club="Putter" startLie="fringe" onResolved={onResolved} />);

    await user.click(screen.getByRole("button", { name: "Count as true putt" }));

    expect(onResolved).toHaveBeenCalledWith("green");
  });

  it("keeps the fringe lie when counted as short game", async () => {
    const onResolved = vi.fn();
    const user = userEvent.setup();
    render(<FringeIsolationPrompt club="Putter" startLie="fringe" onResolved={onResolved} />);

    await user.click(screen.getByRole("button", { name: "Count as short game" }));

    expect(onResolved).toHaveBeenCalledWith("fringe");
  });
});
