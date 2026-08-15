import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useParams } from "next/navigation";
import { IDBFactory } from "fake-indexeddb";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RoundAuditPage from "./page";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
  usePathname: () => "/rounds/42/audit",
}));

const mockUseParams = vi.mocked(useParams);

beforeEach(() => {
  globalThis.indexedDB = new IDBFactory();
  mockUseParams.mockReturnValue({ id: "42" });
});

async function addShot(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Club"), "7-Iron");
  await user.type(screen.getByLabelText("Start distance (yd)"), "150");
  await user.type(screen.getByLabelText("End distance (yd)"), "6");
  await user.click(screen.getByRole("button", { name: "Add shot" }));
}

describe("RoundAuditPage", () => {
  it("renders the round id from the route", () => {
    render(<RoundAuditPage />);
    expect(screen.getByText("Audit round #42")).toBeInTheDocument();
  });

  it("lists shots as they're added and shows a start-review button", async () => {
    const user = userEvent.setup();
    render(<RoundAuditPage />);

    await addShot(user);

    expect(screen.getByText("1 shot entered")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start audit review" })).toBeInTheDocument();
  });

  it("switches to the audit wizard once review starts", async () => {
    const user = userEvent.setup();
    render(<RoundAuditPage />);

    await addShot(user);
    await user.click(screen.getByRole("button", { name: "Start audit review" }));

    expect(await screen.findByText("All caught up")).toBeInTheDocument();
    expect(screen.queryByText("Add a shot")).not.toBeInTheDocument();
  });

  it("accepts decimal distances (e.g. a 0.3y tap-in) without native step validation blocking submit", async () => {
    // Regression test: number inputs default to step="1", which silently
    // blocks form submission for decimal values in a real browser (jsdom
    // doesn't enforce this the same way, so this mainly documents intent —
    // caught via manual browser verification, see the AddShotForm inputs'
    // step="any").
    const user = userEvent.setup();
    render(<RoundAuditPage />);

    await user.type(screen.getByLabelText("Club"), "Putter");
    await user.type(screen.getByLabelText("Start distance (yd)"), "1");
    await user.type(screen.getByLabelText("End distance (yd)"), "0.3");
    await user.click(screen.getByRole("button", { name: "Add shot" }));

    expect(await screen.findByText(/green 0\.3y/)).toBeInTheDocument();
  });
});
