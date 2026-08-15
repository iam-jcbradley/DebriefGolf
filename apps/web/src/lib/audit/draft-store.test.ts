import { beforeEach, describe, expect, it } from "vitest";
import { IDBFactory } from "fake-indexeddb";
import { clearDraft, loadDraft, saveDraft } from "./draft-store";
import type { DraftShot } from "./types";

const sampleShots: DraftShot[] = [
  {
    id: "s1", holeNumber: 1, shotNumber: 1, club: "Driver",
    startLie: "tee", endLie: "fairway", startDistanceYards: 400, endDistanceYards: 150,
  },
];

beforeEach(() => {
  // fresh database per test so state doesn't leak between tests
  globalThis.indexedDB = new IDBFactory();
});

describe("draft-store", () => {
  it("returns null for a round with no saved draft", async () => {
    expect(await loadDraft(999)).toBeNull();
  });

  it("round-trips a saved draft", async () => {
    await saveDraft(1, sampleShots);
    const draft = await loadDraft(1);
    expect(draft?.roundId).toBe(1);
    expect(draft?.shots).toEqual(sampleShots);
    expect(draft?.updatedAt).toBeTruthy();
  });

  it("overwrites the previous draft for the same round", async () => {
    await saveDraft(1, sampleShots);
    const updated = [...sampleShots, { ...sampleShots[0], id: "s2", shotNumber: 2 }];
    await saveDraft(1, updated);

    const draft = await loadDraft(1);
    expect(draft?.shots).toHaveLength(2);
  });

  it("keeps drafts for different rounds independent", async () => {
    await saveDraft(1, sampleShots);
    await saveDraft(2, []);

    expect((await loadDraft(1))?.shots).toEqual(sampleShots);
    expect((await loadDraft(2))?.shots).toEqual([]);
  });

  it("clears a draft", async () => {
    await saveDraft(1, sampleShots);
    await clearDraft(1);
    expect(await loadDraft(1)).toBeNull();
  });
});
