import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter } from "next/navigation";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  getCurrentUser,
  getRounds,
  login,
  logout,
  register,
  setUnauthorizedHandler,
} from "@/lib/api";
import { CurrentUserProvider, useCurrentUser } from "@/lib/current-user";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getCurrentUser: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
  };
});

// `getRounds` and `setUnauthorizedHandler` are deliberately left un-mocked
// above (real `apiFetch` underneath) — the interceptor tests below need the
// genuine wiring between apiFetch's 401 handling and whatever
// CurrentUserProvider registered, not a stand-in for it.
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: vi.fn(),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

const mockGetCurrentUser = vi.mocked(getCurrentUser);
const mockLogin = vi.mocked(login);
const mockLogout = vi.mocked(logout);
const mockRegister = vi.mocked(register);
const mockUseRouter = vi.mocked(useRouter);
const mockPush = vi.fn();

function mockProtectedEndpoint401() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      text: async () => "Not authenticated",
    } as Response)
  );
}

const JANE = {
  id: 6,
  email: "jane@example.com",
  name: "Jane Doe",
  handicap_index: 5,
  created_at: "2026-01-01T00:00:00Z",
};

function Consumer() {
  const { user, loading, signIn, signUp, signOut } = useCurrentUser();
  return (
    <div>
      <p data-testid="loading">{String(loading)}</p>
      <p data-testid="user">{user ? user.name : "none"}</p>
      <button type="button" onClick={() => void signIn("jane@example.com", "pw")}>
        sign in
      </button>
      <button type="button" onClick={() => void signUp("Jane Doe", "jane@example.com", "pw")}>
        sign up
      </button>
      <button type="button" onClick={() => void signOut()}>
        sign out
      </button>
    </div>
  );
}

function renderProvider() {
  return render(
    <CurrentUserProvider>
      <Consumer />
    </CurrentUserProvider>
  );
}

beforeEach(() => {
  mockGetCurrentUser.mockReset();
  mockLogin.mockReset();
  mockLogout.mockReset();
  mockRegister.mockReset();
  mockPush.mockReset();
  mockUseRouter.mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
});

afterEach(() => {
  vi.unstubAllGlobals();
  setUnauthorizedHandler(null);
});

describe("CurrentUserProvider", () => {
  it("resolves the session from the API on mount", async () => {
    mockGetCurrentUser.mockResolvedValue(JANE);

    renderProvider();

    expect(await screen.findByText("Jane Doe")).toBeInTheDocument();
    // Identity comes from the cookie — nothing is passed, and nothing is
    // read from localStorage.
    expect(mockGetCurrentUser).toHaveBeenCalledWith();
  });

  it("is signed out when the API answers 401", async () => {
    mockGetCurrentUser.mockRejectedValue(new ApiError(401, "Not authenticated"));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user")).toHaveTextContent("none");
  });

  it("is signed out when the API is unreachable", async () => {
    // No half-authenticated state: a network failure is treated as signed
    // out rather than trusting a stale local guess, which is what the
    // localStorage-backed version used to do.
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    mockGetCurrentUser.mockRejectedValue(new Error("network down"));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user")).toHaveTextContent("none");
    consoleError.mockRestore();
  });

  it("does not read identity from localStorage", async () => {
    window.localStorage.setItem(
      "debrief-golf-current-user",
      JSON.stringify({ id: 99, name: "Someone Else" })
    );
    mockGetCurrentUser.mockRejectedValue(new ApiError(401, "Not authenticated"));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user")).toHaveTextContent("none");
  });

  it("signIn adopts the returned user", async () => {
    mockGetCurrentUser.mockRejectedValue(new ApiError(401, "Not authenticated"));
    mockLogin.mockResolvedValue(JANE);
    const user = userEvent.setup();

    renderProvider();
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await user.click(screen.getByRole("button", { name: "sign in" }));

    expect(await screen.findByText("Jane Doe")).toBeInTheDocument();
    expect(mockLogin).toHaveBeenCalledWith({ email: "jane@example.com", password: "pw" });
  });

  it("signUp adopts the returned user", async () => {
    mockGetCurrentUser.mockRejectedValue(new ApiError(401, "Not authenticated"));
    mockRegister.mockResolvedValue(JANE);
    const user = userEvent.setup();

    renderProvider();
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await user.click(screen.getByRole("button", { name: "sign up" }));

    expect(await screen.findByText("Jane Doe")).toBeInTheDocument();
  });

  it("signOut clears the user", async () => {
    mockGetCurrentUser.mockResolvedValue(JANE);
    mockLogout.mockResolvedValue({ logged_out: true });
    const user = userEvent.setup();

    renderProvider();
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("button", { name: "sign out" }));

    await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent("none"));
    expect(mockLogout).toHaveBeenCalled();
  });

  it("signOut clears the user even if the request fails", async () => {
    // Leaving the UI claiming someone is signed in after they asked to
    // leave is worse than a cookie that outlives its TTL server-side.
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    mockGetCurrentUser.mockResolvedValue(JANE);
    mockLogout.mockRejectedValue(new Error("network down"));
    const user = userEvent.setup();

    renderProvider();
    await screen.findByText("Jane Doe");

    await user.click(screen.getByRole("button", { name: "sign out" }));

    await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent("none"));
    consoleError.mockRestore();
  });

  it("throws when useCurrentUser is used outside the provider", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Consumer />)).toThrow(
      "useCurrentUser must be used within a CurrentUserProvider"
    );
    consoleError.mockRestore();
  });

  describe("the unauthorized interceptor", () => {
    it("signs out and redirects when a protected call 401s while signed in", async () => {
      mockGetCurrentUser.mockResolvedValue(JANE);
      renderProvider();
      await screen.findByText("Jane Doe");

      mockProtectedEndpoint401();
      await expect(getRounds()).rejects.toBeInstanceOf(ApiError);

      await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent("none"));
      expect(mockPush).toHaveBeenCalledWith("/login?expired=1");
    });

    it("does nothing when nobody was signed in to begin with", async () => {
      // The ordinary shape of browsing while signed out: page loads,
      // getCurrentUser 401s (exempt, handled separately), and some other
      // protected call also 401s. That's not a session that "expired" —
      // there was never one, and bouncing an anonymous visitor to /login
      // the moment they touch a protected page would be wrong.
      mockGetCurrentUser.mockRejectedValue(new ApiError(401, "Not authenticated"));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

      mockProtectedEndpoint401();
      await expect(getRounds()).rejects.toBeInstanceOf(ApiError);

      expect(mockPush).not.toHaveBeenCalled();
      expect(screen.getByTestId("user")).toHaveTextContent("none");
    });

    it("unregisters its handler on unmount", async () => {
      mockGetCurrentUser.mockResolvedValue(JANE);
      const { unmount } = renderProvider();
      await screen.findByText("Jane Doe");

      unmount();

      mockProtectedEndpoint401();
      await expect(getRounds()).rejects.toBeInstanceOf(ApiError);
      // Nothing left mounted to redirect — a call after unmount must not
      // throw trying to invoke a stale handler, and must not navigate.
      expect(mockPush).not.toHaveBeenCalled();
    });
  });
});
