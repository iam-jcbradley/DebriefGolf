import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, resetPassword } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";
import ResetPasswordPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
  useParams: () => ({ token: "a-reset-token" }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/reset-password/a-reset-token",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, resetPassword: vi.fn() };
});

vi.mock("@/lib/current-user", () => ({
  useCurrentUser: vi.fn(),
}));

const mockUseRouter = vi.mocked(useRouter);
const mockResetPassword = vi.mocked(resetPassword);
const mockUseCurrentUser = vi.mocked(useCurrentUser);
const mockPush = vi.fn();
const mockRefresh = vi.fn();

const JANE = {
  id: 1,
  email: "jane@example.com",
  name: "Jane Doe",
  handicap_index: 5,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  mockPush.mockReset();
  mockRefresh.mockReset().mockResolvedValue(undefined);
  mockResetPassword.mockReset();
  mockUseRouter.mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
  mockUseCurrentUser.mockReturnValue({
    user: null,
    loading: false,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    refresh: mockRefresh,
  });
});

describe("ResetPasswordPage", () => {
  it("submits the token from the route and the entered password", async () => {
    mockResetPassword.mockResolvedValue(JANE);
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText("New password"), "a-brand-new-password");
    await user.click(screen.getByRole("button", { name: "Set new password" }));

    expect(mockResetPassword).toHaveBeenCalledWith({
      token: "a-reset-token",
      password: "a-brand-new-password",
    });
  });

  it("re-reads the session and goes to the dashboard on success", async () => {
    mockResetPassword.mockResolvedValue(JANE);
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText("New password"), "a-brand-new-password");
    await user.click(screen.getByRole("button", { name: "Set new password" }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/"));
    expect(mockRefresh).toHaveBeenCalled();
  });

  it("surfaces the backend's message for an invalid or expired token", async () => {
    mockResetPassword.mockRejectedValue(
      new ApiError(422, "This reset link is invalid or has expired")
    );
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText("New password"), "a-brand-new-password");
    await user.click(screen.getByRole("button", { name: "Set new password" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This reset link is invalid or has expired"
    );
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("surfaces a generic message on an unexpected failure", async () => {
    mockResetPassword.mockRejectedValue(new Error("network down"));
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText("New password"), "a-brand-new-password");
    await user.click(screen.getByRole("button", { name: "Set new password" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/something went wrong/i);
  });

  it("offers a way to request a new link", () => {
    render(<ResetPasswordPage />);
    expect(screen.getByRole("link", { name: "Request a new link" })).toHaveAttribute(
      "href",
      "/forgot-password"
    );
  });
});
