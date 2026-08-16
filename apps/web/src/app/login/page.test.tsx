import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "@/app/login/page";
import { ApiError } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";

vi.mock("next/navigation", () => ({
  usePathname: () => "/login",
  useRouter: vi.fn(),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

vi.mock("@/lib/current-user", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/current-user")>();
  return { ...actual, useCurrentUser: vi.fn() };
});

const mockUseCurrentUser = vi.mocked(useCurrentUser);
const mockUseRouter = vi.mocked(useRouter);
const mockPush = vi.fn();
const mockSignIn = vi.fn();
const mockSignUp = vi.fn();

beforeEach(() => {
  mockPush.mockReset();
  mockSignIn.mockReset().mockResolvedValue(undefined);
  mockSignUp.mockReset().mockResolvedValue(undefined);
  mockUseRouter.mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
  mockUseCurrentUser.mockReturnValue({
    user: null,
    loading: false,
    signIn: mockSignIn,
    signUp: mockSignUp,
    signOut: vi.fn(),
    refresh: vi.fn(),
  });
});

describe("LoginPage", () => {
  it("signs in with the entered credentials and goes to the dashboard", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(mockSignIn).toHaveBeenCalledWith("jane@example.com", "correct-horse-battery");
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("does not ask for a name when signing in", () => {
    render(<LoginPage />);
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
  });

  it("switches to account creation and registers", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.click(screen.getByRole("button", { name: "Create one" }));

    await user.type(screen.getByLabelText("Name"), "Jane Doe");
    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(mockSignUp).toHaveBeenCalledWith(
      "Jane Doe",
      "jane@example.com",
      "correct-horse-battery"
    );
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("surfaces the API's message when sign-in fails", async () => {
    mockSignIn.mockRejectedValue(new ApiError(401, "Incorrect email or password"));
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("stays put and reports a generic message on an unexpected failure", async () => {
    mockSignIn.mockRejectedValue(new Error("network down"));
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.type(screen.getByLabelText("Password"), "whatever-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/something went wrong/i);
  });

  it("offers a way out when already signed in", () => {
    mockUseCurrentUser.mockReturnValue({
      user: {
        id: 1,
        name: "Jane Doe",
        email: "jane@example.com",
        handicap_index: 0,
        created_at: "2026-01-01T00:00:00Z",
      },
      loading: false,
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: vi.fn(),
      refresh: vi.fn(),
    });

    render(<LoginPage />);

    expect(screen.getByText(/already signed in/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });
});
