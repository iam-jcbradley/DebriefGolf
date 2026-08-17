import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, requestPasswordReset } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";
import ForgotPasswordPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/forgot-password",
  useParams: () => ({}),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, requestPasswordReset: vi.fn() };
});

vi.mock("@/lib/current-user", () => ({
  useCurrentUser: vi.fn(),
}));

const mockRequestPasswordReset = vi.mocked(requestPasswordReset);
const mockUseCurrentUser = vi.mocked(useCurrentUser);

beforeEach(() => {
  mockRequestPasswordReset.mockReset();
  mockUseCurrentUser.mockReturnValue({
    user: null,
    loading: false,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  });
});

describe("ForgotPasswordPage", () => {
  it("submits the entered email and shows the same notice on success", async () => {
    mockRequestPasswordReset.mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(mockRequestPasswordReset).toHaveBeenCalledWith({ email: "jane@example.com" });
    expect(
      await screen.findByText(/check your email for a reset link/i)
    ).toBeInTheDocument();
  });

  it("shows the same notice even for an email with no account", async () => {
    // The backend answers identically either way (see the route's
    // docstring) — this page has no branch to leak the difference even if
    // it wanted to.
    mockRequestPasswordReset.mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText("Email"), "nobody@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(await screen.findByText(/check your email for a reset link/i)).toBeInTheDocument();
  });

  it("surfaces an error message on an unexpected failure", async () => {
    mockRequestPasswordReset.mockRejectedValue(new Error("network down"));
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/something went wrong/i);
  });

  it("surfaces the API's message on a handled failure", async () => {
    // A syntactically valid address — `type="email"` blocks the browser's
    // own native submission for a malformed one before this component's
    // handler ever runs, so that's not a reachable path to test here.
    mockRequestPasswordReset.mockRejectedValue(new ApiError(422, "Rate limited, try again later"));
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Rate limited, try again later");
  });

  it("links back to sign in", () => {
    render(<ForgotPasswordPage />);
    expect(screen.getByRole("link", { name: "Back to sign in" })).toHaveAttribute(
      "href",
      "/login"
    );
  });
});
