import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";
import { vi } from "vitest";

// Every page renders <NavBar>, which since Phase 10 calls `useRouter()` to
// send you to /login after signing out. Outside a Next app-router context
// that throws, so this provides inert defaults. Tests that assert on
// navigation still declare their own `vi.mock("next/navigation", ...)`,
// which replaces this wholesale.
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
