import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IDBFactory } from "fake-indexeddb";
import { beforeEach, describe, expect, it } from "vitest";
import type { DraftShot } from "@/lib/audit/types";
import { AuditWizard } from "./audit-wizard";

function shot(overrides: Partial<DraftShot>): DraftShot {
  return {
    id: "s1", holeNumber: 1, shotNumber: 1, club: "7-Iron",
    startLie: "fairway", endLie: "green", startDistanceYards: 150, endDistanceYards: 6,
    ...overrides,
  };
}

beforeEach(() => {
  globalThis.indexedDB = new IDBFactory();
});

describe("AuditWizard", () => {
  it("shows an all-caught-up message for a round with nothing to review", async () => {
    render(<AuditWizard roundId={1} initialShots={[shot({ strokesGained: 0.2 })]} />);
    expect(await screen.findByText("All caught up")).toBeInTheDocument();
  });

  it("walks a penalty shot through classification to completion", async () => {
    const shots = [
      shot({
        id: "a", holeNumber: 2, shotNumber: 1, club: "Driver",
        startLie: "tee", endLie: "penalty", startDistanceYards: 385, endDistanceYards: 385,
      }),
    ];
    const user = userEvent.setup();
    render(<AuditWizard roundId={2} initialShots={shots} />);

    expect(await screen.findByText("How was this penalty taken?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "OB / Lost Ball" }));

    expect(await screen.findByText("All caught up")).toBeInTheDocument();
  });

  it("routes a fringe putt through isolation then putt routing", async () => {
    const shots = [
      shot({
        id: "a", club: "Putter", startLie: "fringe", endLie: "green",
        startDistanceYards: 1, endDistanceYards: 0.3,
      }),
    ];
    const user = userEvent.setup();
    render(<AuditWizard roundId={3} initialShots={shots} />);

    expect(await screen.findByText("Was this putt actually on the green?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Count as true putt" }));

    // now a confirmed green putt at 1 yard (3ft) — well inside the short-putt range
    expect(await screen.findByText("Did this putt go in?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Made it" }));

    expect(await screen.findByText("All caught up")).toBeInTheDocument();
  });

  it("shows the strike quality modal for a badly-struck shot and resolves on tag", async () => {
    const shots = [shot({ id: "a", strokesGained: -0.9 })];
    const user = userEvent.setup();
    render(<AuditWizard roundId={4} initialShots={shots} />);

    expect(await screen.findByText("What happened on that shot?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fat" }));

    expect(await screen.findByText("All caught up")).toBeInTheDocument();
  });

  it("shows the count of remaining shots and current hole/shot number", async () => {
    const shots = [shot({ id: "a", holeNumber: 5, shotNumber: 3, strokesGained: -0.9 })];
    render(<AuditWizard roundId={5} initialShots={shots} />);

    expect(await screen.findByText(/1 shot to review · Hole 5, shot 3/)).toBeInTheDocument();
  });

  it("persists progress across a remount via IndexedDB", async () => {
    const shots = [shot({ id: "a", strokesGained: -0.9 })];
    const user = userEvent.setup();
    const { unmount } = render(<AuditWizard roundId={6} initialShots={shots} />);

    await screen.findByText("What happened on that shot?");
    await user.click(screen.getByRole("button", { name: "Fat" }));
    await screen.findByText("All caught up");
    unmount();

    // remount with the *original* unreviewed shots — the saved draft should win
    render(<AuditWizard roundId={6} initialShots={shots} />);
    expect(await screen.findByText("All caught up")).toBeInTheDocument();
  });
});
