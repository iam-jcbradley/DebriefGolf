import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useCurrentUser } from "@/lib/current-user";
import { usePracticeData } from "@/lib/use-practice-data";
import PracticePage from "./page";

vi.mock("@/lib/current-user", () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock("@/lib/use-practice-data", () => ({
  usePracticeData: vi.fn(),
}));

const mockUseCurrentUser = vi.mocked(useCurrentUser);
const mockUsePracticeData = vi.mocked(usePracticeData);

const testUser = { id: 7, name: "Jane Doe" };
const mockRefresh = vi.fn();

beforeEach(() => {
  mockRefresh.mockReset();
  mockUseCurrentUser.mockReturnValue({
    user: testUser,
    loading: false,
    openPicker: vi.fn(),
    clearUser: vi.fn(),
  });
  mockUsePracticeData.mockReturnValue({ state: { status: "idle" }, refresh: mockRefresh });
});

describe("PracticePage", () => {
  it("shows the no-player empty state when no player is chosen", () => {
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: false,
      openPicker: vi.fn(),
      clearUser: vi.fn(),
    });
    render(<PracticePage />);
    expect(screen.getByText("Choose a player to continue")).toBeInTheDocument();
  });

  it("shows the upload panel scoped to the current player", () => {
    render(<PracticePage />);
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
  });

  it("shows a loading state", () => {
    mockUsePracticeData.mockReturnValue({ state: { status: "loading" }, refresh: mockRefresh });
    render(<PracticePage />);
    expect(screen.getByText(/loading practice data/i)).toBeInTheDocument();
  });

  it("shows an error state", () => {
    mockUsePracticeData.mockReturnValue({
      state: { status: "error", message: "network down" },
      refresh: mockRefresh,
    });
    render(<PracticePage />);
    expect(screen.getByRole("alert")).toHaveTextContent("network down");
  });

  it("shows a no-weaknesses message when ready with no combines", () => {
    mockUsePracticeData.mockReturnValue({
      state: {
        status: "ready",
        delivery: { user_id: 7, session_count: 0, clubs: [], trend: {}, sim_vs_real_gapping: [] },
        combines: { user_id: 7, weaknesses: [], combines: [] },
      },
      refresh: mockRefresh,
    });
    render(<PracticePage />);
    expect(screen.getByText(/no weaknesses detected/i)).toBeInTheDocument();
  });
});
