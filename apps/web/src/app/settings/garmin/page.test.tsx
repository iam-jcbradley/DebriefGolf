import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSearchParams } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  disconnectGarmin,
  getGarminStatus,
  startGarminAuthorize,
} from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";
import GarminSettingsPage from "./page";

vi.mock("next/navigation", () => ({
  useSearchParams: vi.fn(),
  usePathname: () => "/settings/garmin",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    startGarminAuthorize: vi.fn(),
    getGarminStatus: vi.fn(),
    disconnectGarmin: vi.fn(),
  };
});

vi.mock("@/lib/current-user", () => ({
  useCurrentUser: vi.fn(),
}));

const mockStartAuthorize = vi.mocked(startGarminAuthorize);
const mockGetStatus = vi.mocked(getGarminStatus);
const mockDisconnect = vi.mocked(disconnectGarmin);
const mockUseSearchParams = vi.mocked(useSearchParams);
const mockUseCurrentUser = vi.mocked(useCurrentUser);

const testUser = { id: 6, name: "Jane Doe", email: "player@example.com", handicap_index: 0, created_at: "2026-01-01T00:00:00Z" };

beforeEach(() => {
  mockStartAuthorize.mockReset();
  mockGetStatus.mockReset();
  mockGetStatus.mockResolvedValue({ connected: false });
  mockDisconnect.mockReset();
  mockUseSearchParams.mockReturnValue(new URLSearchParams() as ReturnType<typeof useSearchParams>);
  mockUseCurrentUser.mockReturnValue({
    user: testUser,
    loading: false,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  });
});

describe("GarminSettingsPage", () => {
  it("shows the signed-out empty state when nobody is signed in", () => {
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      refresh: vi.fn(),
    });
    render(<GarminSettingsPage />);
    expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
  });

  it("renders the connect panel for the current player", () => {
    render(<GarminSettingsPage />);
    expect(screen.getByRole("heading", { name: "Garmin Connect" })).toBeInTheDocument();
    // The NavBar renders the signed-in name too, so scope this to the
    // panel's own emphasis element.
    expect(screen.getByText("Jane Doe", { selector: "strong" })).toBeInTheDocument();
  });

  it("shows a connected-success banner when redirected back with ?connected=1", () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams("connected=1") as ReturnType<typeof useSearchParams>
    );
    render(<GarminSettingsPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Garmin account connected");
  });

  it("shows an error banner when redirected back with ?error=...", () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams("error=access_denied") as ReturnType<typeof useSearchParams>
    );
    render(<GarminSettingsPage />);
    expect(screen.getByRole("alert")).toHaveTextContent("access_denied");
  });

  it("fetches and displays connection status for the current player", async () => {
    mockGetStatus.mockResolvedValue({ connected: true });

    render(<GarminSettingsPage />);

    expect(await screen.findByText("Connected")).toBeInTheDocument();
    expect(mockGetStatus).toHaveBeenCalledWith();
  });

  it("shows a Disconnect button only once connected", async () => {
    mockGetStatus.mockResolvedValue({ connected: true });

    render(<GarminSettingsPage />);

    expect(await screen.findByRole("button", { name: "Disconnect" })).toBeInTheDocument();
  });

  it("starts the Garmin authorize flow when Connect is clicked", async () => {
    mockGetStatus.mockResolvedValue({ connected: false });
    mockStartAuthorize.mockResolvedValue({ authorize_url: "https://example.com/oauthConfirm?x=1" });
    const user = userEvent.setup();

    render(<GarminSettingsPage />);
    await screen.findByText("Not connected");
    await user.click(screen.getByRole("button", { name: "Connect Garmin" }));

    expect(mockStartAuthorize).toHaveBeenCalledWith();
  });

  it("disconnects and updates status when Disconnect is clicked", async () => {
    mockGetStatus.mockResolvedValue({ connected: true });
    mockDisconnect.mockResolvedValue({ connected: false });
    const user = userEvent.setup();

    render(<GarminSettingsPage />);
    await user.click(await screen.findByRole("button", { name: "Disconnect" }));

    expect(mockDisconnect).toHaveBeenCalledWith();
    expect(await screen.findByText("Not connected")).toBeInTheDocument();
  });
});
