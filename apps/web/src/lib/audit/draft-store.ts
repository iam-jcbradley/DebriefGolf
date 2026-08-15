import type { DraftShot } from "@/lib/audit/types";

// PRD §10 Phase 3 "IndexedDB layer for offline-friendly audit wizard draft
// state": persists a round's in-progress shot review so a refresh or a
// dropped connection doesn't lose the user's work.
const DB_NAME = "debrief-golf-audit-drafts";
const DB_VERSION = 1;
const STORE_NAME = "drafts";

export interface AuditDraft {
  roundId: number;
  shots: DraftShot[];
  updatedAt: string;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "roundId" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function saveDraft(roundId: number, shots: DraftShot[]): Promise<void> {
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const draft: AuditDraft = { roundId, shots, updatedAt: new Date().toISOString() };
      tx.objectStore(STORE_NAME).put(draft);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

export async function loadDraft(roundId: number): Promise<AuditDraft | null> {
  const db = await openDb();
  try {
    return await new Promise<AuditDraft | null>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const request = tx.objectStore(STORE_NAME).get(roundId);
      request.onsuccess = () => resolve((request.result as AuditDraft | undefined) ?? null);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

export async function clearDraft(roundId: number): Promise<void> {
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).delete(roundId);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
