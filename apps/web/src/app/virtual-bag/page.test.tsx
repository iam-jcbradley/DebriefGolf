import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useCurrentUser } from "@/lib/current-user";
import { useVirtualRounds } from "@/lib/use-virtual-rounds";
import VirtualBagPage from "./page";

vi.mock("@/lib/current-user", () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock("@/lib/use-virtual-rounds", () => ({
  useVirtualRounds: vi.fn(),
}));

const mockUseCurrentUser = vi.mocked(useCurrentUser);
const mockUseVirtualRounds = vi.mocked(useVirtualRounds);

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
  mockUseVirtualRounds.mockReturnValue({ state: { status: "idle" }, refresh: mockRefresh });
});

describe("VirtualBagPage", () => {
  it("shows the no-player empty state when no player is chosen", () => {
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: false,
      openPicker: vi.fn(),
      clearUser: vi.fn(),
    });
    render(<VirtualBagPage />);
    expect(screen.getByText("Choose a player to continue")).toBeInTheDocument();
  });

  it("shows the log-a-round panel scoped to the current player", () => {
    render(<VirtualBagPage />);
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
  });

  it("shows a loading state", () => {
    mockUseVirtualRounds.mockReturnValue({ state: { status: "loading" }, refresh: mockRefresh });
    render(<VirtualBagPage />);
    expect(screen.getByText(/loading virtual rounds/i)).toBeInTheDocument();
  });

  it("shows an error state", () => {
    mockUseVirtualRounds.mockReturnValue({
      state: { status: "error", message: "network down" },
      refresh: mockRefresh,
    });
    render(<VirtualBagPage />);
    expect(screen.getByRole("alert")).toHaveTextContent("network down");
  });

  it("renders the virtual round list when ready", () => {
    mockUseVirtualRounds.mockReturnValue({
      state: { status: "ready", rounds: [] },
      refresh: mockRefresh,
    });
    render(<VirtualBagPage />);
    expect(screen.getByText(/no virtual rounds logged yet/i)).toBeInTheDocument();
  });
});
