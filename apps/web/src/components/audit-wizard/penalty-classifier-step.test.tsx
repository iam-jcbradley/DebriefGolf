import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PenaltyDropContext } from "@/lib/audit/penalty-classifier";
import { PenaltyClassifierStep } from "./penalty-classifier-step";

const context: PenaltyDropContext = {
  precedingShotStartLie: "fairway",
  precedingShotStartDistanceYards: 140,
  enteredHazardDistanceYards: 140,
};

describe("PenaltyClassifierStep", () => {
  it("renders both classification options", () => {
    render(<PenaltyClassifierStep context={context} onClassified={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Lateral Hazard" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "OB / Lost Ball" })).toBeInTheDocument();
  });

  it("calls onClassified with the lateral hazard drop result", async () => {
    const onClassified = vi.fn();
    const user = userEvent.setup();
    render(<PenaltyClassifierStep context={context} onClassified={onClassified} />);

    await user.click(screen.getByRole("button", { name: "Lateral Hazard" }));

    expect(onClassified).toHaveBeenCalledWith({
      penaltyType: "lateral_hazard",
      dropLie: "rough",
      dropDistanceYards: 140,
      tag: "Penalty: Lateral Hazard Drop",
    });
  });

  it("calls onClassified with the OB/lost ball drop result", async () => {
    const onClassified = vi.fn();
    const user = userEvent.setup();
    render(<PenaltyClassifierStep context={context} onClassified={onClassified} />);

    await user.click(screen.getByRole("button", { name: "OB / Lost Ball" }));

    expect(onClassified).toHaveBeenCalledWith({
      penaltyType: "ob_lost_ball",
      dropLie: "fairway",
      dropDistanceYards: 140,
      tag: "Penalty: Stroke & Distance",
    });
  });
});
