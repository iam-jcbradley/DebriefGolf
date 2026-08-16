import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter, useSearchParams } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createRound, getCourses, type CourseListItem, type RoundSummary } from "@/lib/api";
import { useCurrentUser } from "@/lib/current-user";
import NewRoundPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
  useSearchParams: vi.fn(),
  usePathname: () => "/rounds/new",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getCourses: vi.fn(),
    createRound: vi.fn(),
  };
});

vi.mock("@/lib/current-user", () => ({
  useCurrentUser: vi.fn(),
}));

const mockUseRouter = vi.mocked(useRouter);
const mockUseSearchParams = vi.mocked(useSearchParams);
const mockGetCourses = vi.mocked(getCourses);
const mockCreateRound = vi.mocked(createRound);
const mockUseCurrentUser = vi.mocked(useCurrentUser);

const testUser = { id: 9, name: "Jane Doe", email: "player@example.com", handicap_index: 0, created_at: "2026-01-01T00:00:00Z" };

const courses: CourseListItem[] = [
  { id: 1, name: "Pinehurst Creek Golf Club", city: "Pawleys Island", state: "SC" },
];

const mockPush = vi.fn();

beforeEach(() => {
  mockPush.mockReset();
  mockUseRouter.mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
  mockUseSearchParams.mockReturnValue(
    new URLSearchParams() as unknown as ReturnType<typeof useSearchParams>
  );
  mockGetCourses.mockReset();
  mockCreateRound.mockReset();
  mockGetCourses.mockResolvedValue(courses);
  mockUseCurrentUser.mockReturnValue({
    user: testUser,
    loading: false,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  });
});

describe("NewRoundPage", () => {
  it("shows the signed-out empty state when nobody is signed in", () => {
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      refresh: vi.fn(),
    });
    render(<NewRoundPage />);
    expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
  });

  it("renders the form with courses loaded", async () => {
    render(<NewRoundPage />);
    expect(await screen.findByText("Pinehurst Creek Golf Club — Pawleys Island")).toBeInTheDocument();
    // The NavBar renders the signed-in name too, so scope this to the
    // panel's own emphasis element.
    expect(screen.getByText("Jane Doe", { selector: "strong" })).toBeInTheDocument();
  });

  it("prefills the course from a course_id query param", async () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams("course_id=1") as unknown as ReturnType<typeof useSearchParams>
    );
    render(<NewRoundPage />);
    await screen.findByText("Pinehurst Creek Golf Club — Pawleys Island");
    expect(screen.getByLabelText("Course")).toHaveValue("1");
  });

  it("shows a validation error when no course is chosen", async () => {
    const user = userEvent.setup();
    render(<NewRoundPage />);
    await screen.findByText("Pinehurst Creek Golf Club — Pawleys Island");

    await user.click(screen.getByRole("button", { name: "Create round" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/course/i);
    expect(mockCreateRound).not.toHaveBeenCalled();
  });

  it("creates a round and redirects to the shot-entry page", async () => {
    mockCreateRound.mockResolvedValue({
      id: 55, user_id: 9, course_id: 1, played_at: "2026-08-15", total_score: null,
      status: "needs_audit",
    } as RoundSummary);
    const user = userEvent.setup();
    render(<NewRoundPage />);
    await screen.findByText("Pinehurst Creek Golf Club — Pawleys Island");

    await user.selectOptions(screen.getByLabelText("Course"), "1");
    await user.click(screen.getByRole("button", { name: "Create round" }));

    // No user_id: the round is attributed to the session user server-side.
    expect(mockCreateRound).toHaveBeenCalledWith(
      expect.objectContaining({ course_id: 1 })
    );
    expect(mockPush).toHaveBeenCalledWith("/rounds/55/enter");
  });

  it("shows an error when round creation fails", async () => {
    mockCreateRound.mockRejectedValue(new Error("boom"));
    const user = userEvent.setup();
    render(<NewRoundPage />);
    await screen.findByText("Pinehurst Creek Golf Club — Pawleys Island");

    await user.selectOptions(screen.getByLabelText("Course"), "1");
    await user.click(screen.getByRole("button", { name: "Create round" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(mockPush).not.toHaveBeenCalled();
  });
});
