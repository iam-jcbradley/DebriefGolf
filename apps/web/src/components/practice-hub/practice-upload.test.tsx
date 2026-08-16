import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, uploadPracticeSession } from "@/lib/api";
import { PracticeUpload } from "./practice-upload";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, uploadPracticeSession: vi.fn() };
});

const mockUpload = vi.mocked(uploadPracticeSession);

function makeFile(name = "session.csv") {
  return new File(["Club,Carry\nDriver,250"], name, { type: "text/csv" });
}

beforeEach(() => {
  mockUpload.mockReset();
});

describe("PracticeUpload", () => {
  it("uploads the chosen file with the selected source", async () => {
    mockUpload.mockResolvedValue({ session_id: 3, shot_count: 3, errors: [] });
    const onUploaded = vi.fn();
    const user = userEvent.setup();

    render(<PracticeUpload onUploaded={onUploaded} />);
    const input = screen.getByLabelText(/upload r10\/r50 session export/i);
    await user.upload(input, makeFile());

    expect(await screen.findByRole("status")).toHaveTextContent("3");
    expect(mockUpload).toHaveBeenCalledWith("R10", expect.any(File));
    expect(onUploaded).toHaveBeenCalledWith({ session_id: 3, shot_count: 3, errors: [] });
  });

  it("uploads with the selected device when changed", async () => {
    mockUpload.mockResolvedValue({ session_id: 4, shot_count: 1, errors: [] });
    const user = userEvent.setup();

    render(<PracticeUpload />);
    await user.selectOptions(screen.getByLabelText(/device/i), "R50");
    const input = screen.getByLabelText(/upload r10\/r50 session export/i);
    await user.upload(input, makeFile());

    expect(mockUpload).toHaveBeenCalledWith("R50", expect.any(File));
  });


  it("shows the API error message when the upload fails", async () => {
    mockUpload.mockRejectedValue(new ApiError(422, "No shots could be parsed"));
    const user = userEvent.setup();

    render(<PracticeUpload />);
    const input = screen.getByLabelText(/upload r10\/r50 session export/i);
    await user.upload(input, makeFile());

    expect(await screen.findByRole("alert")).toHaveTextContent("No shots could be parsed");
  });

  it("surfaces a partial-parse-error count on success", async () => {
    mockUpload.mockResolvedValue({
      session_id: 5,
      shot_count: 2,
      errors: ["row 3: missing required field 'club'"],
    });
    const user = userEvent.setup();

    render(<PracticeUpload />);
    const input = screen.getByLabelText(/upload r10\/r50 session export/i);
    await user.upload(input, makeFile());

    expect(await screen.findByRole("status")).toHaveTextContent("1 row(s)");
  });
});
