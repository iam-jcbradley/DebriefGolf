import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSearchParams } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  disconnectGarmin,
  getGarminStatus,
  startGarminAuthorize,
} from "@/lib/api";
import GarminSettingsPage from "./page";

vi.mock("next/navigation", () => ({
  useSearchParams: vi.fn(),
  usePathname: () => "/settings/garmin",
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

const mockStartAuthorize = vi.mocked(startGarminAuthorize);
const mockGetStatus = vi.mocked(getGarminStatus);
const mockDisconnect = vi.mocked(disconnectGarmin);
const mockUseSearchParams = vi.mocked(useSearchParams);

beforeEach(() => {
  mockStartAuthorize.mockReset();
  mockGetStatus.mockReset();
  mockDisconnect.mockReset();
  mockUseSearchParams.mockReturnValue(new URLSearchParams() as ReturnType<typeof useSearchParams>);
});

describe("GarminSettingsPage", () => {
  it("renders the connect panel with a user id input", () => {
    render(<GarminSettingsPage />);
    expect(screen.getByRole("heading", { name: "Garmin Connect" })).toBeInTheDocument();
    expect(screen.getByLabelText("User ID")).toBeInTheDocument();
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

  it("fetches and displays connection status once a user id is entered", async () => {
    mockGetStatus.mockResolvedValue({ connected: true });
    const user = userEvent.setup();

    render(<GarminSettingsPage />);
    await user.type(screen.getByLabelText("User ID"), "6");

    expect(await screen.findByText("Connected")).toBeInTheDocument();
    expect(mockGetStatus).toHaveBeenCalledWith(6);
  });

  it("shows a Disconnect button only once connected", async () => {
    mockGetStatus.mockResolvedValue({ connected: true });
    const user = userEvent.setup();

    render(<GarminSettingsPage />);
    expect(screen.queryByRole("button", { name: "Disconnect" })).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("User ID"), "6");
    expect(await screen.findByRole("button", { name: "Disconnect" })).toBeInTheDocument();
  });

  it("starts the Garmin authorize flow when Connect is clicked", async () => {
    mockGetStatus.mockResolvedValue({ connected: false });
    mockStartAuthorize.mockResolvedValue({ authorize_url: "https://example.com/oauthConfirm?x=1" });
    const user = userEvent.setup();

    render(<GarminSettingsPage />);
    await user.type(screen.getByLabelText("User ID"), "6");
    await user.click(screen.getByRole("button", { name: "Connect Garmin" }));

    expect(mockStartAuthorize).toHaveBeenCalledWith(6);
  });

  it("disconnects and updates status when Disconnect is clicked", async () => {
    mockGetStatus.mockResolvedValue({ connected: true });
    mockDisconnect.mockResolvedValue({ connected: false });
    const user = userEvent.setup();

    render(<GarminSettingsPage />);
    await user.type(screen.getByLabelText("User ID"), "6");
    await user.click(await screen.findByRole("button", { name: "Disconnect" }));

    expect(mockDisconnect).toHaveBeenCalledWith(6);
    expect(await screen.findByText("Not connected")).toBeInTheDocument();
  });

  it("disables Connect Garmin until a user id is entered", () => {
    render(<GarminSettingsPage />);
    expect(screen.getByRole("button", { name: "Connect Garmin" })).toBeDisabled();
  });
});
