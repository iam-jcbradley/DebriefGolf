import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, getUserProfile } from "@/lib/api";
import { CurrentUserProvider, useCurrentUser } from "@/lib/current-user";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getUserProfile: vi.fn(), searchUsers: vi.fn(), createUser: vi.fn() };
});

const mockGetUserProfile = vi.mocked(getUserProfile);

const STORAGE_KEY = "debrief-golf-current-user";

function Consumer() {
  const { user, loading, openPicker, clearUser } = useCurrentUser();
  return (
    <div>
      <p data-testid="loading">{String(loading)}</p>
      <p data-testid="user">{user ? user.name : "none"}</p>
      <button type="button" onClick={openPicker}>
        open
      </button>
      <button type="button" onClick={clearUser}>
        clear
      </button>
    </div>
  );
}

beforeEach(() => {
  mockGetUserProfile.mockReset();
  window.localStorage.clear();
});

describe("CurrentUserProvider", () => {
  it("starts with no user when localStorage is empty", async () => {
    render(
      <CurrentUserProvider>
        <Consumer />
      </CurrentUserProvider>
    );
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user")).toHaveTextContent("none");
  });

  it("restores a stored user after re-validating it against the backend", async () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ id: 6, name: "Jane Doe" }));
    mockGetUserProfile.mockResolvedValue({
      id: 6, email: "jane@example.com", name: "Jane Doe", handicap_index: 5,
      created_at: "2026-01-01T00:00:00Z",
    });

    render(
      <CurrentUserProvider>
        <Consumer />
      </CurrentUserProvider>
    );

    expect(await screen.findByTestId("user")).toHaveTextContent("Jane Doe");
    expect(mockGetUserProfile).toHaveBeenCalledWith(6);
  });

  it("clears a stored user that no longer exists (404)", async () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ id: 6, name: "Jane Doe" }));
    mockGetUserProfile.mockRejectedValue(new ApiError(404, "User not found"));

    render(
      <CurrentUserProvider>
        <Consumer />
      </CurrentUserProvider>
    );

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user")).toHaveTextContent("none");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("keeps the cached user on a non-404 (network) error", async () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ id: 6, name: "Jane Doe" }));
    mockGetUserProfile.mockRejectedValue(new Error("network down"));

    render(
      <CurrentUserProvider>
        <Consumer />
      </CurrentUserProvider>
    );

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user")).toHaveTextContent("Jane Doe");
  });

  it("ignores malformed localStorage content", async () => {
    window.localStorage.setItem(STORAGE_KEY, "not json");

    render(
      <CurrentUserProvider>
        <Consumer />
      </CurrentUserProvider>
    );

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user")).toHaveTextContent("none");
    expect(mockGetUserProfile).not.toHaveBeenCalled();
  });

  it("clearUser removes the persisted player", async () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ id: 6, name: "Jane Doe" }));
    mockGetUserProfile.mockResolvedValue({
      id: 6, email: "jane@example.com", name: "Jane Doe", handicap_index: 5,
      created_at: "2026-01-01T00:00:00Z",
    });
    const user = userEvent.setup();

    render(
      <CurrentUserProvider>
        <Consumer />
      </CurrentUserProvider>
    );
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("button", { name: "clear" }));

    expect(screen.getByTestId("user")).toHaveTextContent("none");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("openPicker opens the player switcher dialog", async () => {
    const user = userEvent.setup();
    render(
      <CurrentUserProvider>
        <Consumer />
      </CurrentUserProvider>
    );
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await user.click(screen.getByRole("button", { name: "open" }));

    expect(await screen.findByText("Who's playing?")).toBeInTheDocument();
  });

  it("throws when useCurrentUser is used outside the provider", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Consumer />)).toThrow(
      "useCurrentUser must be used within a CurrentUserProvider"
    );
    consoleError.mockRestore();
  });
});
