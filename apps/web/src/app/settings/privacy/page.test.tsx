import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, deleteUserData, getUserDataExport } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";
import PrivacySettingsPage from "./page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/privacy",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getUserDataExport: vi.fn(), deleteUserData: vi.fn() };
});

vi.mock("@/lib/current-user", () => ({
  useCurrentUser: vi.fn(),
}));

const mockGetExport = vi.mocked(getUserDataExport);
const mockDelete = vi.mocked(deleteUserData);
const mockUseCurrentUser = vi.mocked(useCurrentUser);

const testUser = { id: 6, name: "Jane Doe", email: "player@example.com", handicap_index: 0, created_at: "2026-01-01T00:00:00Z" };
const mockSignOut = vi.fn();

beforeEach(() => {
  mockGetExport.mockReset();
  mockDelete.mockReset();
  mockSignOut.mockReset();
  mockUseCurrentUser.mockReturnValue({
    user: testUser,
    loading: false,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: mockSignOut,
    refresh: vi.fn(),
  });
  vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:mock"), revokeObjectURL: vi.fn() });
});

describe("PrivacySettingsPage", () => {
  it("shows the signed-out empty state when nobody is signed in", () => {
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: mockSignOut,
      refresh: vi.fn(),
    });
    render(<PrivacySettingsPage />);
    expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
  });

  it("renders the settings tabs, export panel, delete panel, and notice for the current player", () => {
    render(<PrivacySettingsPage />);
    expect(screen.getByRole("link", { name: "Garmin Connect" })).toBeInTheDocument();
    expect(screen.getByText("Download Your Data")).toBeInTheDocument();
    expect(screen.getByText("Delete My Account")).toBeInTheDocument();
    expect(screen.getByText(/pending legal review/i)).toBeInTheDocument();
    // The NavBar renders the signed-in name too, so scope this to the
    // panel's own emphasis element.
    expect(screen.getByText("Jane Doe", { selector: "strong" })).toBeInTheDocument();
  });

  it("exports data for the current player", async () => {
    mockGetExport.mockResolvedValue({
      user: { id: 6, email: "a@b.com", name: "A", handicap_index: 5, created_at: "2026-01-01" },
      garmin_connected: false,
      rounds: [],
      practice_sessions: [],
      virtual_rounds: [],
    });
    const user = userEvent.setup();

    render(<PrivacySettingsPage />);
    await user.click(screen.getByRole("button", { name: /download my data/i }));

    expect(mockGetExport).toHaveBeenCalledWith();
  });

  it("shows an error when export fails", async () => {
    mockGetExport.mockRejectedValue(new ApiError(404, "User not found"));
    const user = userEvent.setup();

    render(<PrivacySettingsPage />);
    await user.click(screen.getByRole("button", { name: /download my data/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("User not found");
  });

  it("requires typing DELETE before the destructive delete button is enabled", async () => {
    const user = userEvent.setup();
    render(<PrivacySettingsPage />);
    await user.click(screen.getByRole("button", { name: "Delete my account" }));

    const confirmButton = screen.getByRole("button", { name: /permanently delete my account/i });
    expect(confirmButton).toBeDisabled();

    await user.type(screen.getByLabelText(/type delete to confirm/i), "DELETE");
    expect(confirmButton).toBeEnabled();
  });

  it("deletes the account, signs out, and shows confirmation", async () => {
    mockDelete.mockResolvedValue({ deleted: true, user_id: 6 });
    const user = userEvent.setup();

    render(<PrivacySettingsPage />);
    await user.click(screen.getByRole("button", { name: "Delete my account" }));
    await user.type(screen.getByLabelText(/type delete to confirm/i), "DELETE");
    await user.click(screen.getByRole("button", { name: /permanently delete my account/i }));

    expect(mockDelete).toHaveBeenCalledWith();
    expect(await screen.findByRole("status")).toHaveTextContent(/have been deleted/i);
    expect(mockSignOut).toHaveBeenCalled();
  });

  it("cancel returns to the initial delete button without calling the API", async () => {
    const user = userEvent.setup();
    render(<PrivacySettingsPage />);
    await user.click(screen.getByRole("button", { name: "Delete my account" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByRole("button", { name: "Delete my account" })).toBeInTheDocument();
    expect(mockDelete).not.toHaveBeenCalled();
  });
});
