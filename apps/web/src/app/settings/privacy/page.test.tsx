import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, deleteUserData, getUserDataExport } from "@/lib/api";
import PrivacySettingsPage from "./page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/privacy",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getUserDataExport: vi.fn(), deleteUserData: vi.fn() };
});

const mockGetExport = vi.mocked(getUserDataExport);
const mockDelete = vi.mocked(deleteUserData);

beforeEach(() => {
  mockGetExport.mockReset();
  mockDelete.mockReset();
  vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:mock"), revokeObjectURL: vi.fn() });
});

describe("PrivacySettingsPage", () => {
  it("renders the settings tabs, export panel, delete panel, and notice", () => {
    render(<PrivacySettingsPage />);
    expect(screen.getByRole("link", { name: "Garmin Connect" })).toBeInTheDocument();
    expect(screen.getByText("Download Your Data")).toBeInTheDocument();
    expect(screen.getByText("Delete My Account")).toBeInTheDocument();
    expect(screen.getByText(/pending legal review/i)).toBeInTheDocument();
  });

  it("exports data for the entered user id", async () => {
    mockGetExport.mockResolvedValue({
      user: { id: 6, email: "a@b.com", name: "A", handicap_index: 5, created_at: "2026-01-01" },
      garmin_connected: false,
      rounds: [],
      practice_sessions: [],
      virtual_rounds: [],
    });
    const user = userEvent.setup();

    render(<PrivacySettingsPage />);
    await user.type(screen.getByLabelText("User ID"), "6");
    await user.click(screen.getByRole("button", { name: /download my data/i }));

    expect(mockGetExport).toHaveBeenCalledWith(6);
  });

  it("shows an error when export fails", async () => {
    mockGetExport.mockRejectedValue(new ApiError(404, "User not found"));
    const user = userEvent.setup();

    render(<PrivacySettingsPage />);
    await user.type(screen.getByLabelText("User ID"), "999");
    await user.click(screen.getByRole("button", { name: /download my data/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("User not found");
  });

  it("requires typing DELETE before the destructive delete button is enabled", async () => {
    const user = userEvent.setup();
    render(<PrivacySettingsPage />);
    await user.type(screen.getByLabelText("User ID"), "6");
    await user.click(screen.getByRole("button", { name: "Delete my account" }));

    const confirmButton = screen.getByRole("button", { name: /permanently delete my account/i });
    expect(confirmButton).toBeDisabled();

    await user.type(screen.getByLabelText(/type delete to confirm/i), "DELETE");
    expect(confirmButton).toBeEnabled();
  });

  it("deletes the account and shows confirmation once DELETE is typed and confirmed", async () => {
    mockDelete.mockResolvedValue({ deleted: true, user_id: 6 });
    const user = userEvent.setup();

    render(<PrivacySettingsPage />);
    await user.type(screen.getByLabelText("User ID"), "6");
    await user.click(screen.getByRole("button", { name: "Delete my account" }));
    await user.type(screen.getByLabelText(/type delete to confirm/i), "DELETE");
    await user.click(screen.getByRole("button", { name: /permanently delete my account/i }));

    expect(mockDelete).toHaveBeenCalledWith(6);
    expect(await screen.findByRole("status")).toHaveTextContent(/have been deleted/i);
  });

  it("cancel returns to the initial delete button without calling the API", async () => {
    const user = userEvent.setup();
    render(<PrivacySettingsPage />);
    await user.type(screen.getByLabelText("User ID"), "6");
    await user.click(screen.getByRole("button", { name: "Delete my account" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByRole("button", { name: "Delete my account" })).toBeInTheDocument();
    expect(mockDelete).not.toHaveBeenCalled();
  });

  it("disables the delete-my-account button until a user id is entered", () => {
    render(<PrivacySettingsPage />);
    expect(screen.getByRole("button", { name: "Delete my account" })).toBeDisabled();
  });
});
