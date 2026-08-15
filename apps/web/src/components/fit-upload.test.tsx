import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, uploadFitFile } from "@/lib/api";
import { FitUpload } from "./fit-upload";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, uploadFitFile: vi.fn() };
});

const mockUploadFitFile = vi.mocked(uploadFitFile);

function makeFile(name = "round.fit") {
  return new File([new Uint8Array([1, 2, 3])], name, { type: "application/octet-stream" });
}

beforeEach(() => {
  mockUploadFitFile.mockReset();
});

describe("FitUpload", () => {
  it("uploads the chosen file for the given user and reports success", async () => {
    mockUploadFitFile.mockResolvedValue({
      round_id: 5, status: "needs_audit", sport: "golf", point_count: 120,
    });
    const onUploaded = vi.fn();
    const user = userEvent.setup();

    render(<FitUpload userId={7} onUploaded={onUploaded} />);
    const input = screen.getByLabelText("Upload .FIT file", { selector: "input" });
    await user.upload(input, makeFile());

    expect(await screen.findByRole("status")).toHaveTextContent("needs audit");
    expect(mockUploadFitFile).toHaveBeenCalledWith(7, expect.any(File));
    expect(onUploaded).toHaveBeenCalledWith({
      round_id: 5, status: "needs_audit", sport: "golf", point_count: 120,
    });
  });

  it("shows an error and does not call the API when no user id is set", async () => {
    const user = userEvent.setup();
    render(<FitUpload userId={null} />);
    const input = screen.getByLabelText("Upload .FIT file", { selector: "input" });

    await user.upload(input, makeFile());

    expect(await screen.findByRole("alert")).toHaveTextContent(/user id/i);
    expect(mockUploadFitFile).not.toHaveBeenCalled();
  });

  it("shows the API error message when the upload fails", async () => {
    mockUploadFitFile.mockRejectedValue(new ApiError(404, "User not found"));
    const user = userEvent.setup();

    render(<FitUpload userId={999} />);
    const input = screen.getByLabelText("Upload .FIT file", { selector: "input" });
    await user.upload(input, makeFile());

    expect(await screen.findByRole("alert")).toHaveTextContent("User not found");
  });

  it("handles a file dropped onto the dropzone", async () => {
    mockUploadFitFile.mockResolvedValue({
      round_id: 1, status: "casual_practice", sport: null, point_count: 0,
    });

    render(<FitUpload userId={7} />);
    const dropzone = screen.getByTestId("fit-upload-dropzone");
    const file = makeFile();

    const dataTransfer = { files: [file] };
    dropzone.dispatchEvent(
      Object.assign(new Event("drop", { bubbles: true, cancelable: true }), { dataTransfer })
    );

    expect(await screen.findByRole("status")).toHaveTextContent("casual practice");
  });
});
