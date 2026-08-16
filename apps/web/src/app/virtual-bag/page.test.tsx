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

const testUser = { id: 7, name: "Jane Doe", email: "player@example.com", handicap_index: 0, created_at: "2026-01-01T00:00:00Z" };
const mockRefresh = vi.fn();

beforeEach(() => {
  mockRefresh.mockReset();
  mockUseCurrentUser.mockReturnValue({
    user: testUser,
    loading: false,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  });
  mockUseVirtualRounds.mockReturnValue({ state: { status: "idle" }, refresh: mockRefresh });
});

describe("VirtualBagPage", () => {
  it("shows the signed-out empty state when nobody is signed in", () => {
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      refresh: vi.fn(),
    });
    render(<VirtualBagPage />);
    expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
  });

  it("shows the log-a-round panel scoped to the current player", () => {
    render(<VirtualBagPage />);
    // The NavBar renders the signed-in name too, so scope this to the
    // panel's own emphasis element.
    expect(screen.getByText("Jane Doe", { selector: "strong" })).toBeInTheDocument();
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
