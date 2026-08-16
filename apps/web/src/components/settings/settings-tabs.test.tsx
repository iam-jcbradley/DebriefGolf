import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SettingsTabs } from "./settings-tabs";

const mockUsePathname = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

describe("SettingsTabs", () => {
  it("marks the current tab as active", () => {
    mockUsePathname.mockReturnValue("/settings/privacy");
    render(<SettingsTabs />);
    expect(screen.getByRole("link", { name: "Privacy & Data" })).toHaveAttribute(
      "aria-current",
      "page"
    );
    expect(screen.getByRole("link", { name: "Garmin Connect" })).not.toHaveAttribute(
      "aria-current"
    );
  });

  it("links to both settings pages", () => {
    mockUsePathname.mockReturnValue("/settings/garmin");
    render(<SettingsTabs />);
    expect(screen.getByRole("link", { name: "Garmin Connect" })).toHaveAttribute(
      "href",
      "/settings/garmin"
    );
    expect(screen.getByRole("link", { name: "Privacy & Data" })).toHaveAttribute(
      "href",
      "/settings/privacy"
    );
  });
});
