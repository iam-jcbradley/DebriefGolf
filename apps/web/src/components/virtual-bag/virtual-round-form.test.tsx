import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, createVirtualRound } from "@/lib/api";
import { VirtualRoundForm } from "./virtual-round-form";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, createVirtualRound: vi.fn() };
});

const mockCreate = vi.mocked(createVirtualRound);

beforeEach(() => {
  mockCreate.mockReset();
});

describe("VirtualRoundForm", () => {
  it("submits the entered course, platform, and score", async () => {
    mockCreate.mockResolvedValue({
      id: 1, user_id: 7, platform: "gspro", course_name: "Pebble Beach",
      played_at: "2026-08-15T00:00:00Z", holes_played: 18, total_score: 82, notes: null,
    });
    const onCreated = vi.fn();
    const user = userEvent.setup();

    render(<VirtualRoundForm onCreated={onCreated} />);
    await user.type(screen.getByLabelText(/course/i), "Pebble Beach");
    await user.type(screen.getByLabelText(/total score/i), "82");
    await user.click(screen.getByRole("button", { name: /log round/i }));

    expect(mockCreate).toHaveBeenCalledWith({
      platform: "gspro", course_name: "Pebble Beach", total_score: 82,
    });
    expect(await screen.findByRole("button", { name: /log round/i })).toBeEnabled();
    expect(onCreated).toHaveBeenCalled();
  });


  it("shows an error when the course name is blank", async () => {
    const user = userEvent.setup();
    render(<VirtualRoundForm />);
    await user.click(screen.getByRole("button", { name: /log round/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/course name/i);
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("shows the API error message when the save fails", async () => {
    mockCreate.mockRejectedValue(new ApiError(404, "User not found"));
    const user = userEvent.setup();

    render(<VirtualRoundForm />);
    await user.type(screen.getByLabelText(/course/i), "Pebble Beach");
    await user.click(screen.getByRole("button", { name: /log round/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("User not found");
  });
});
