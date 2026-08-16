import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  getRoundAnalytics,
  getRounds,
  isPendingAnalytics,
  uploadFitFile,
} from "./api";

function mockFetchOnce(status: number, body: unknown, ok = status >= 200 && status < 300) {
  const response = {
    ok,
    status,
    statusText: "",
    json: async () => body,
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  } as Response;
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  return response;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("getRounds", () => {
  it("returns parsed JSON on success", async () => {
    const rounds = [{ id: 1, played_at: "2026-08-15", total_score: 78, course_id: 1, user_id: 1, status: "verified" }];
    mockFetchOnce(200, rounds);

    await expect(getRounds()).resolves.toEqual(rounds);
  });

  it("throws ApiError with status on a non-ok response", async () => {
    mockFetchOnce(404, "Round not found");

    await expect(getRounds()).rejects.toBeInstanceOf(ApiError);
    await expect(getRounds()).rejects.toMatchObject({ status: 404 });
  });

  it("extracts a clean message from a FastAPI JSON error body", async () => {
    mockFetchOnce(404, { detail: "User not found" });

    await expect(getRounds()).rejects.toMatchObject({ message: "User not found" });
  });

  it("joins messages from a FastAPI validation error body", async () => {
    mockFetchOnce(422, { detail: [{ msg: "field required" }, { msg: "must be positive" }] });

    await expect(getRounds()).rejects.toMatchObject({
      message: "field required; must be positive",
    });
  });
});

describe("isPendingAnalytics", () => {
  it("identifies a pending (shot-less) analytics response", () => {
    expect(isPendingAnalytics({ round_id: 1, status: "needs_audit", needs_shots: true })).toBe(
      true
    );
  });

  it("identifies a full analytics response as not pending", () => {
    expect(
      isPendingAnalytics({
        round_id: 1,
        handicap_bucket: 10,
        strokes_gained: { total: 0, by_category: { OTT: 0, APP: 0, ARG: 0, PUTT: 0 } },
        tiger_five: {
          double_bogeys_or_worse: 0, three_putts: 0, par_five_bogeys: 0,
          blown_recoveries_inside_50: 0, penalties_inside_150: 0, clean_card_index: 100,
        },
        putting: {
          lag_putt_count: 0, lag_efficiency_pct: null, average_lag_proximity_yards: null,
          short_putt_count: 0, start_line_conversion_pct: null,
        },
        shots: [],
      })
    ).toBe(false);
  });
});

describe("getRoundAnalytics", () => {
  it("fetches the analytics endpoint for the given round id", async () => {
    const response = mockFetchOnce(200, { round_id: 5, status: "needs_audit", needs_shots: true });
    await getRoundAnalytics(5);

    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/rounds/5/analytics"),
      // Every request is credentialed so the session cookie is sent.
      expect.objectContaining({ credentials: "include" })
    );
    void response;
  });
});

describe("uploadFitFile", () => {
  it("POSTs the file as multipart form data to the upload endpoint", async () => {
    mockFetchOnce(200, { round_id: 9, status: "needs_audit", sport: "golf", point_count: 42 });
    const file = new File([new Uint8Array([1, 2, 3])], "round.fit");

    const result = await uploadFitFile(file);

    expect(result.round_id).toBe(9);
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/rounds/upload");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBe(file);
  });
});
