import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StrikeQualityModal } from "./strike-quality-modal";

describe("StrikeQualityModal", () => {
  it("renders nothing when closed", () => {
    render(
      <StrikeQualityModal open={false} strokesGained={-0.8} onTag={vi.fn()} onSkip={vi.fn()} />
    );
    expect(screen.queryByText("What happened on that shot?")).not.toBeInTheDocument();
  });

  it("shows the strokes-gained cost and every tag option when open", () => {
    render(
      <StrikeQualityModal open strokesGained={-0.82} onTag={vi.fn()} onSkip={vi.fn()} />
    );
    expect(screen.getByText("What happened on that shot?")).toBeInTheDocument();
    expect(screen.getByText(/cost you 0.82 strokes/)).toBeInTheDocument();
    for (const tag of ["Toe", "Heel", "Fat", "Thin", "Push", "Pull", "Skulled", "Chunked"]) {
      expect(screen.getByRole("button", { name: tag })).toBeInTheDocument();
    }
  });

  it("calls onTag with the chosen tag", async () => {
    const onTag = vi.fn();
    const user = userEvent.setup();
    render(<StrikeQualityModal open strokesGained={-0.6} onTag={onTag} onSkip={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Toe" }));

    expect(onTag).toHaveBeenCalledWith("Toe");
  });

  it("calls onSkip when Skip is clicked", async () => {
    const onSkip = vi.fn();
    const user = userEvent.setup();
    render(<StrikeQualityModal open strokesGained={-0.6} onTag={vi.fn()} onSkip={onSkip} />);

    await user.click(screen.getByRole("button", { name: "Skip" }));

    expect(onSkip).toHaveBeenCalled();
  });

  it("calls onSkip when dismissed via Escape", async () => {
    const onSkip = vi.fn();
    const user = userEvent.setup();
    render(<StrikeQualityModal open strokesGained={-0.6} onTag={vi.fn()} onSkip={onSkip} />);

    await user.keyboard("{Escape}");

    expect(onSkip).toHaveBeenCalled();
  });
});
