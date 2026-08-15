import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PuttRoutingStep } from "./putt-routing-step";

describe("PuttRoutingStep", () => {
  it("routes a short putt to a made/missed prompt", () => {
    render(
      <PuttRoutingStep
        startDistanceYards={1}
        onShortPuttResult={vi.fn()}
        onLongPuttResult={vi.fn()}
      />
    );
    expect(screen.getByText("Did this putt go in?")).toBeInTheDocument();
    expect(screen.queryByLabelText(/close did you leave it/)).not.toBeInTheDocument();
  });

  it("reports a made short putt", async () => {
    const onShortPuttResult = vi.fn();
    const user = userEvent.setup();
    render(
      <PuttRoutingStep
        startDistanceYards={1}
        onShortPuttResult={onShortPuttResult}
        onLongPuttResult={vi.fn()}
      />
    );

    await user.click(screen.getByRole("button", { name: "Made it" }));
    expect(onShortPuttResult).toHaveBeenCalledWith(true);
  });

  it("reports a missed short putt", async () => {
    const onShortPuttResult = vi.fn();
    const user = userEvent.setup();
    render(
      <PuttRoutingStep
        startDistanceYards={1}
        onShortPuttResult={onShortPuttResult}
        onLongPuttResult={vi.fn()}
      />
    );

    await user.click(screen.getByRole("button", { name: "Missed" }));
    expect(onShortPuttResult).toHaveBeenCalledWith(false);
  });

  it("routes a long putt to a lag proximity input", () => {
    render(
      <PuttRoutingStep
        startDistanceYards={10}
        onShortPuttResult={vi.fn()}
        onLongPuttResult={vi.fn()}
      />
    );
    expect(screen.getByLabelText(/close did you leave it/)).toBeInTheDocument();
    expect(screen.queryByText("Did this putt go in?")).not.toBeInTheDocument();
  });

  it("reports the lag proximity for a long putt", async () => {
    const onLongPuttResult = vi.fn();
    const user = userEvent.setup();
    render(
      <PuttRoutingStep
        startDistanceYards={10}
        onShortPuttResult={vi.fn()}
        onLongPuttResult={onLongPuttResult}
      />
    );

    await user.type(screen.getByLabelText(/close did you leave it/), "3");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(onLongPuttResult).toHaveBeenCalledWith(3);
  });

  it("disables Save until a proximity is entered", () => {
    render(
      <PuttRoutingStep
        startDistanceYards={10}
        onShortPuttResult={vi.fn()}
        onLongPuttResult={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("shows no special prompt for a mid-range putt", () => {
    render(
      <PuttRoutingStep
        startDistanceYards={5}
        onShortPuttResult={vi.fn()}
        onLongPuttResult={vi.fn()}
      />
    );
    expect(screen.getByText("No special review needed for this putt.")).toBeInTheDocument();
    expect(screen.queryByText("Did this putt go in?")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/close did you leave it/)).not.toBeInTheDocument();
  });
});
